import json
from datetime import datetime
from dateutil import parser as dateparser
from flask import request
from .models import User
from . import db

def current_user_id():
    """Extract user id from header; default for demo."""
    return request.headers.get('X-User-Id', 'demo_user')

# def ensure_user(db_session, uid: str):
#     """Create a user row if absent (simple demo mechanism)."""
#     if uid and not User.query.get(uid):
#         db_session.add(User(id=uid, email=None, name=None))
#         db_session.commit()

def ensure_user(db_session, uid: str):
    if uid and db_session.get(User, uid) is None:
        db_session.add(User(id=uid, email=None, name=None))
        db_session.commit()

def parse_iso_date(s: str):
    try:
        return dateparser.parse(s)
    except Exception:
        return None

def extract_keys_recursive(obj, prefix="", acc=None):
    """Return list of dot-keys for dicts/lists."""
    if acc is None: acc = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            acc.append(path)
            extract_keys_recursive(v, path, acc)
    elif isinstance(obj, list):
        # For arrays, include index wildcard notation (e.g., items[].price)
        path = f"{prefix}[]" if prefix else "[]"
        acc.append(path)
        for i, v in enumerate(obj[:3]):  # sample first few for shape
            extract_keys_recursive(v, f"{prefix}[{i}]", acc)
    return acc
