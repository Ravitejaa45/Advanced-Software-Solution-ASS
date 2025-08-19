from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import and_
from io import StringIO
import io, csv
import json
from datetime import datetime, timezone
from dateutil import parser as dateparser

from .. import db
from ..models import Rule, RuleCondition, Payload, PayloadLabel
from ..services import current_user_id, ensure_user, parse_iso_date, extract_keys_recursive
from ..rule_engine import apply_rules

api_bp = Blueprint('api', __name__)

def _serialize_rule(rule: Rule):
    return {
        "id": rule.id,
        "name": rule.name,
        "label": rule.label,
        "priority": rule.priority,
        "active": rule.active,
        "conditions": [
            {
                "id": c.id,
                "group": c.group_id,
                "key_path": c.key_path,
                "operator": c.operator,
                "value": json.loads(c.value_json)
            } for c in rule.conditions
        ]
    }

@api_bp.route('/keys/extract', methods=['POST'])
def extract_keys():
    """
    Extract dot-keys from sample JSON.
    ---
    parameters:
      - in: body
        name: body
        schema:
          type: object
    responses:
      200:
        description: key list
    """
    data = request.get_json(force=True, silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Provide a sample JSON object"}), 400
    keys = extract_keys_recursive(data)
    return jsonify({"keys": sorted(set(keys))})

@api_bp.route('/rules', methods=['GET'])
def list_rules():
    """List rules for current user."""
    uid = current_user_id()
    ensure_user(db.session, uid)
    rules = Rule.query.filter_by(user_id=uid).order_by(Rule.priority.asc()).all()
    return jsonify([_serialize_rule(r) for r in rules])

@api_bp.route('/rules', methods=['POST'])
def create_rule():
    """
    Create a new rule.
    Expected JSON:
    {
      "name": "Rule Name",
      "label": "Green",
      "priority": 10,
      "active": true,
      "conditions": [
        {"group": 1, "key_path": "Product", "operator": "=", "value": "Chocolate"},
        {"group": 1, "key_path": "Price", "operator": "<", "value": 2}
      ]
    }
    """
    uid = current_user_id()
    ensure_user(db.session, uid)
    body = request.get_json(force=True, silent=True) or {}
    try:
        name = body['name'].strip()
        label = body['label'].strip()
        priority = int(body.get('priority', 100))
        active = bool(body.get('active', True))
        conditions = body.get('conditions', [])
        if not name or not label or not conditions:
            return jsonify({"error": "name, label, and conditions are required"}), 400
    except Exception:
        return jsonify({"error": "Invalid rule payload"}), 400

    # Basic validation of operators & types
    allowed_ops = {'=','!=','<','>','<=','>='}
    for c in conditions:
        if c.get('operator') not in allowed_ops:
            return jsonify({"error": f"Invalid operator: {c.get('operator')}"}), 400
        if not isinstance(c.get('key_path'), str):
            return jsonify({"error": "key_path must be string"}), 400
        # value can be any JSON literal (string/number/bool/null)
        json.dumps(c.get('value'))

    rule = Rule(user_id=uid, name=name, label=label, priority=priority, active=active)
    db.session.add(rule); db.session.flush()
    for c in conditions:
        db.session.add(RuleCondition(
            rule_id=rule.id,
            group_id=int(c.get('group', 1)),
            key_path=c['key_path'],
            operator=c['operator'],
            value_json=json.dumps(c.get('value'))
        ))
    db.session.commit()
    return jsonify({"message": "created", "id": rule.id}), 201

@api_bp.route('/rules/<int:rid>', methods=['PUT'])
def update_rule(rid: int):
    uid = current_user_id()
    rule = Rule.query.filter_by(id=rid, user_id=uid).first()
    if not rule:
        return jsonify({"error": "rule not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    if 'name' in body: rule.name = body['name']
    if 'label' in body: rule.label = body['label']
    if 'priority' in body: rule.priority = int(body['priority'])
    if 'active' in body: rule.active = bool(body['active'])
    if 'conditions' in body:
        # replace all conditions
        for c in list(rule.conditions):
            db.session.delete(c)
        for c in body['conditions']:
            db.session.add(RuleCondition(
                rule_id=rule.id,
                group_id=int(c.get('group', 1)),
                key_path=c['key_path'],
                operator=c['operator'],
                value_json=json.dumps(c.get('value'))
            ))
    db.session.commit()
    return jsonify({"message": "updated"})

@api_bp.route('/rules/<int:rid>', methods=['DELETE'])
def delete_rule(rid: int):
    uid = current_user_id()
    rule = Rule.query.filter_by(id=rid, user_id=uid).first()
    if not rule:
        return jsonify({"error": "rule not found"}), 404
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "deleted"})

@api_bp.route('/rules/<int:rid>/toggle', methods=['POST'])
def toggle_rule(rid: int):
    uid = current_user_id()
    rule = Rule.query.filter_by(id=rid, user_id=uid).first()
    if not rule:
        return jsonify({"error": "rule not found"}), 404
    rule.active = not rule.active
    db.session.commit()
    return jsonify({"message": "toggled", "active": rule.active})

@api_bp.route('/process', methods=['POST'])
def process_payload():
    """
    Process an incoming JSON payload, apply active rules, store labels, return result.
    """
    uid = current_user_id()
    ensure_user(db.session, uid)

    payload = request.get_json(force=True, silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Payload must be a JSON object"}), 400

    # fetch active rules (ordered by priority) and serialize for engine
    q = Rule.query.filter_by(user_id=uid, active=True).order_by(Rule.priority.asc()).all()
    rules = []
    for r in q:
        conds = []
        for c in r.conditions:
            conds.append((c.group_id, c.operator, c.key_path, json.loads(c.value_json)))
        rules.append({"id": r.id, "label": r.label, "priority": r.priority, "conditions": conds})

    labels, rule_ids = apply_rules(payload, rules)

    single = request.args.get('single_label', 'false').lower() in {'1', 'true', 'yes'}
    if single and rule_ids:
        priority_by_id = {r['id']: r['priority'] for r in rules}
        # pick the rule_id with the LOWEST priority number
        top_rid = min(rule_ids, key=lambda rid: (priority_by_id.get(rid, 10**9), rid))
        labels = [next(r['label'] for r in rules if r['id'] == top_rid)]
        rule_ids = [top_rid]

    p = Payload(user_id=uid, payload_json=json.dumps(payload))
    db.session.add(p); db.session.flush()

    id_to_label = {r['id']: r['label'] for r in rules}
    for rid in rule_ids:
        db.session.add(PayloadLabel(payload_id=p.id, rule_id=rid, label=id_to_label[rid]))
        
    db.session.commit()

    return jsonify({
        "labels": labels,
        "applied_rule_ids": rule_ids,
        # "processed_at": datetime.utcnow().isoformat() + "Z"
        "processed_at": datetime.now(timezone.utc).isoformat()

    })

@api_bp.route('/statistics', methods=['GET'])
def statistics():
    """
    Return totals and breakdown by label.
    Query params: label (optional), from, to (ISO datetime, optional)
    """
    uid = current_user_id()
    label = request.args.get('label')
    from_s = request.args.get('from')
    to_s = request.args.get('to')
    from_dt = parse_iso_date(from_s) if from_s else None
    to_dt = parse_iso_date(to_s) if to_s else None

    # Base payload range
    q = Payload.query.filter_by(user_id=uid)
    if from_dt:
        q = q.filter(Payload.received_at >= from_dt)
    if to_dt:
        q = q.filter(Payload.received_at <= to_dt)
    payloads = q.all()
    total = len(payloads)
    # Collect labels
    by_label = {}
    if total > 0:
        ids = [p.id for p in payloads]
        lab_q = PayloadLabel.query.filter(PayloadLabel.payload_id.in_(ids))
        if label:
            lab_q = lab_q.filter(PayloadLabel.label == label)
        for pl in lab_q.all():
            by_label[pl.label] = by_label.get(pl.label, 0) + 1

    breakdown = [{"label": k, "count": v, "percentage": (v*100.0/total if total else 0.0)}
                 for k, v in sorted(by_label.items(), key=lambda x: x[0])]
    return jsonify({"total_payloads": total, "by_label": breakdown})

# @api_bp.route('/statistics/export', methods=['GET'])
# def export_statistics():
#     """
#     Export statistics as CSV.
#     """
#     res = statistics().json
#     output = StringIO()
#     writer = csv.writer(output)
#     writer.writerow(["label", "count", "percentage"])
#     for row in res.get('by_label', []):
#         writer.writerow([row['label'], row['count'], f"{row['percentage']:.2f}"])
#     output.seek(0)
#     return send_file(
#         path_or_file=StringIO(output.read()),
#         mimetype='text/csv',
#         as_attachment=True,
#         download_name='statistics.csv'
#     )

@api_bp.get('/statistics/export')
def export_statistics():
    """
    Export statistics as CSV (uses BytesIO so send_file works cross-platform).
    Reuses the /api/statistics logic for user scoping & filters.
    """
    # Call the existing endpoint to compute stats (includes X-User-Id + query params)
    resp = statistics()
    stats = resp.get_json()  # <-- use get_json(), not .json

    # Build CSV into a text buffer (newline='' to avoid blank lines on Windows)
    text_buf = io.StringIO(newline="")
    writer = csv.writer(text_buf)
    writer.writerow(["label", "count", "percentage"])
    for row in stats.get("by_label", []):
        writer.writerow([row["label"], row["count"], f'{row["percentage"]:.2f}'])

    # Optional totals line
    writer.writerow([])
    writer.writerow(["total_payloads", stats.get("total_payloads", 0)])

    # Convert text -> bytes (with UTF-8 BOM so Excel opens cleanly), then send_file
    byte_buf = io.BytesIO(text_buf.getvalue().encode("utf-8-sig"))
    byte_buf.seek(0)

    user_id = current_user_id()
    filename = f"statistics_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"

    return send_file(
        byte_buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )
