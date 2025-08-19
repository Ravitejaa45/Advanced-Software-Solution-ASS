from typing import Any, Dict, List, Tuple
import numbers

def get_by_path(obj: Any, path: str):
    cur = obj
    for seg in path.replace(']', '').split('.'):
        if seg == '':
            continue
        if '[' in seg:
            name, idx = seg.split('[')
            if not isinstance(cur, dict) or name not in cur:
                return _Missing
            cur = cur[name]
            try:
                idx = int(idx)
            except Exception:
                return _Missing
            if not isinstance(cur, list) or idx >= len(cur):
                return _Missing
            cur = cur[idx]
        else:
            if not isinstance(cur, dict) or seg not in cur:
                return _Missing
            cur = cur[seg]
    return cur

class _MissingType: pass
_Missing = _MissingType()

def _coerce_numeric(x):
    if isinstance(x, numbers.Number):
        return x
    if isinstance(x, str):
        try: return float(x)
        except Exception: return None
    return None

def _compare(op: str, left, right):
    if op in ('<','>','<=','>='):
        lnum, rnum = _coerce_numeric(left), _coerce_numeric(right)
        if lnum is None or rnum is None:
            return False
        return {
            '<': lnum < rnum,
            '>': lnum > rnum,
            '<=': lnum <= rnum,
            '>=': lnum >= rnum
        }[op]
    if op == '=':
        return left == right
    if op == '!=':
        return left != right
    return False

def evaluate_rule(payload: Dict[str, Any], conditions: List[Tuple[int, str, Any, Any]]):
    if not conditions:
        return False
    groups = {}
    for g, op, key_path, val in conditions:
        groups.setdefault(g, []).append((op, key_path, val))
    for g_id, conds in groups.items():
        and_ok = True
        for op, key_path, val in conds:
            v = get_by_path(payload, key_path)
            if v is _Missing:
                and_ok = False
                break
            if not _compare(op, v, val):
                and_ok = False
                break
        if and_ok:
            return True
    return False

def apply_rules(payload: Dict[str, Any], rules: List[Dict]) -> Tuple[List[str], List[int]]:
    matched = []
    for r in rules:
        if evaluate_rule(payload, r['conditions']):
            matched.append((r['priority'], r['label'], r['id']))
    matched.sort(key=lambda x: x[0])
    labels = []
    rule_ids = []
    seen = set()
    for _, lab, rid in matched:
        if lab not in seen:
            seen.add(lab)
            labels.append(lab)
        rule_ids.append(rid)
    return labels, rule_ids
