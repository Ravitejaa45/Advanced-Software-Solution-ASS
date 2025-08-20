from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import and_
from io import StringIO
import io, csv
import json
from datetime import datetime, timezone
from dateutil import parser as dateparser
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_socketio import SocketIO, emit
from app import socketio 

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
    data = request.get_json(force=True, silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Provide a sample JSON object"}), 400
    keys = extract_keys_recursive(data)
    return jsonify({"keys": sorted(set(keys))})

@api_bp.route('/rules', methods=['GET'])
def list_rules():
    uid = current_user_id()
    ensure_user(db.session, uid)
    rules = Rule.query.filter_by(user_id=uid).order_by(Rule.priority.asc()).all()
    return jsonify([_serialize_rule(r) for r in rules])

@api_bp.route('/rules', methods=['POST'])
def create_rule():
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

    allowed_ops = {'=','!=','<','>','<=','>='}
    for c in conditions:
        if c.get('operator') not in allowed_ops:
            return jsonify({"error": f"Invalid operator: {c.get('operator')}"}), 400
        if not isinstance(c.get('key_path'), str):
            return jsonify({"error": "key_path must be string"}), 400
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
    uid = current_user_id()
    ensure_user(db.session, uid)

    payload = request.get_json(force=True, silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Payload must be a JSON object"}), 400

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
        top_rid = min(rule_ids, key=lambda rid: (priority_by_id.get(rid, 10**9), rid))
        labels = [next(r['label'] for r in rules if r['id'] == top_rid)]
        rule_ids = [top_rid]

    p = Payload(user_id=uid, payload_json=json.dumps(payload))
    db.session.add(p); db.session.flush()

    id_to_label = {r['id']: r['label'] for r in rules}
    for rid in rule_ids:
        db.session.add(PayloadLabel(payload_id=p.id, rule_id=rid, label=id_to_label[rid]))
        
    db.session.commit()

    total = Payload.query.filter_by(user_id=uid).count()
    by_label = {}
    for label in labels:
        by_label[label] = by_label.get(label, 0) + 1

    breakdown = [{"label": k, "count": v, "percentage": (v*100.0/total if total else 0.0)}
                 for k, v in sorted(by_label.items(), key=lambda x: x[0])]

    socketio.emit('stats_update', {"total_payloads": total, "by_label": breakdown})

    return jsonify({
        "labels": labels,
        "applied_rule_ids": rule_ids,
        "processed_at": datetime.now(timezone.utc).isoformat()

    })

@api_bp.route('/statistics', methods=['GET'])
def statistics():
    uid = current_user_id()
    label = request.args.get('label')
    from_s = request.args.get('from')
    to_s = request.args.get('to')
    from_dt = parse_iso_date(from_s) if from_s else None
    to_dt = parse_iso_date(to_s) if to_s else None

    q = Payload.query.filter_by(user_id=uid)
    if from_dt:
        q = q.filter(Payload.received_at >= from_dt)
    if to_dt:
        q = q.filter(Payload.received_at <= to_dt)
    payloads = q.all()
    total = len(payloads)
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


@api_bp.route('/statistics/socket', methods=['GET'])
def statistics_socket():
    uid = current_user_id()
    label = request.args.get('label')
    from_s = request.args.get('from')
    to_s = request.args.get('to')
    
    from_dt = parse_iso_date(from_s) if from_s else None
    to_dt = parse_iso_date(to_s) if to_s else None

    q = Payload.query.filter_by(user_id=uid)

    if from_dt:
        q = q.filter(Payload.received_at >= from_dt)
    if to_dt:
        q = q.filter(Payload.received_at <= to_dt)
    
    payloads = q.all()
    total = len(payloads)
    
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

    stats = {"total_payloads": total, "by_label": breakdown}

    socketio.emit('stats_update', stats)

    return jsonify(stats)


@api_bp.get('/statistics/export')
def export_statistics():
    resp = statistics()
    stats = resp.get_json()

    return generate_csv(stats)

    # export_format = request.args.get('format', 'csv').lower()

    # if export_format == 'pdf':
    #     return generate_pdf(stats)
    # else:
    #     return generate_csv(stats)
    
# @api_bp.get('/statistics/export.pdf')
# def export_statistics_pdf():
#     resp = statistics()
#     return generate_pdf(resp.get_json())

@api_bp.get('/statistics/export.csv')
def export_statistics_csv():
    resp = statistics()
    return generate_csv(resp.get_json())

def generate_csv(stats):
    text_buf = io.StringIO(newline="")
    writer = csv.writer(text_buf)
    writer.writerow(["label", "count", "percentage"])
    for row in stats.get("by_label", []):
        writer.writerow([row["label"], row["count"], f'{row["percentage"]:.2f}'])

    writer.writerow([])
    writer.writerow(["total_payloads", stats.get("total_payloads", 0)])

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

# def generate_pdf(stats):
#     user_id = current_user_id()
#     filename = f"statistics_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pdf"

#     buffer = io.BytesIO()
#     c = canvas.Canvas(buffer, pagesize=letter)
#     width, height = letter

#     c.setFont("Helvetica-Bold", 16)
#     c.drawString(50, height - 40, "Statistics Report")

#     c.setFont("Helvetica", 12)
#     c.drawString(50, height - 60, f"Total Payloads: {stats.get('total_payloads', 0)}")
#     c.drawString(50, height - 80, "Labels Breakdown:")

#     y_position = height - 120
#     c.drawString(50, y_position, "Label")
#     c.drawString(200, y_position, "Count")
#     c.drawString(350, y_position, "Percentage")

#     y_position -= 20
#     for row in stats.get("by_label", []):
#         c.drawString(50, y_position, row["label"])
#         c.drawString(200, y_position, str(row["count"]))
#         c.drawString(350, y_position, f'{row["percentage"]:.2f}%')
#         y_position -= 20

#         if y_position < 100:
#             c.showPage()
#             y_position = height - 40
#             c.setFont("Helvetica", 12)
#             c.drawString(50, y_position, "Labels Breakdown:")
#             y_position -= 20

#     c.drawString(50, y_position - 20, f"Total Payloads: {stats.get('total_payloads', 0)}")

#     c.showPage()
#     c.save()

#     buffer.seek(0)

#     return send_file(
#         buffer,
#         mimetype="application/pdf",
#         as_attachment=True,
#         download_name=filename,
#     )

