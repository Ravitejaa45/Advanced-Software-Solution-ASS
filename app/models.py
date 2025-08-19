from datetime import datetime, timezone
import json
from . import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(64), primary_key=True)  # e.g., header X-User-Id
    email = db.Column(db.String(255))
    name = db.Column(db.String(255))
    # created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Rule(db.Model):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.id'), index=True, nullable=True)
    name = db.Column(db.String(255), nullable=False)
    label = db.Column(db.String(128), nullable=False)
    priority = db.Column(db.Integer, default=100)  # lower = higher priority
    active = db.Column(db.Boolean, default=True)
    # created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conditions = db.relationship("RuleCondition", backref="rule", cascade="all, delete-orphan")

class RuleCondition(db.Model):
    __tablename__ = 'rule_conditions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rules.id'), index=True, nullable=False)
    group_id = db.Column(db.Integer, default=1)  # DNF: groups OR'ed, inner conditions AND'ed
    key_path = db.Column(db.String(512), nullable=False)  # e.g., "Price" or "order.total.amount"
    operator = db.Column(db.String(8), nullable=False)    # =, !=, <, >, <=, >=
    value_json = db.Column(db.Text, nullable=False)       # store as JSON string for type fidelity

    def value(self):
        try:
            return json.loads(self.value_json)
        except Exception:
            return self.value_json

class Payload(db.Model):
    __tablename__ = 'payloads'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.id'), index=True, nullable=True)
    payload_json = db.Column(db.Text, nullable=False)
    # received_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    received_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    labels = db.relationship("PayloadLabel", backref="payload", cascade="all, delete-orphan")

    def payload(self):
        return json.loads(self.payload_json)

class PayloadLabel(db.Model):
    __tablename__ = 'payload_labels'
    payload_id = db.Column(db.Integer, db.ForeignKey('payloads.id'), primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rules.id'))
    label = db.Column(db.String(128), index=True)

def seed_demo_data():
    """Create demo user + a few demo rules for 'Chocolate' pricing bands."""
    from . import db
    if not User.query.get('demo_user'):
        db.session.add(User(id='demo_user', email='demo@example.com', name='Demo'))
        db.session.commit()

    if Rule.query.filter_by(user_id='demo_user').count() == 0:
        # Product=Chocolate & Price < 2 -> Green
        r1 = Rule(user_id='demo_user', name='Choco Low', label='Green', priority=10, active=True)
        db.session.add(r1); db.session.flush()
        db.session.add(RuleCondition(rule_id=r1.id, group_id=1, key_path='Product', operator='=', value_json='"Chocolate"'))
        db.session.add(RuleCondition(rule_id=r1.id, group_id=1, key_path='Price', operator='<', value_json='2'))

        # Product=Chocolate & 2 <= Price < 5 -> Yellow
        r2 = Rule(user_id='demo_user', name='Choco Mid', label='Yellow', priority=20, active=True)
        db.session.add(r2); db.session.flush()
        db.session.add(RuleCondition(rule_id=r2.id, group_id=1, key_path='Product', operator='=', value_json='"Chocolate"'))
        db.session.add(RuleCondition(rule_id=r2.id, group_id=1, key_path='Price', operator='>=', value_json='2'))
        db.session.add(RuleCondition(rule_id=r2.id, group_id=1, key_path='Price', operator='<', value_json='5'))

        # Product=Chocolate & Price >= 5 -> Red
        r3 = Rule(user_id='demo_user', name='Choco High', label='Red', priority=30, active=True)
        db.session.add(r3); db.session.flush()
        db.session.add(RuleCondition(rule_id=r3.id, group_id=1, key_path='Product', operator='=', value_json='"Chocolate"'))
        db.session.add(RuleCondition(rule_id=r3.id, group_id=1, key_path='Price', operator='>=', value_json='5'))

        # (CompanyName='Google') OR (CompanyName='Amazon' AND Price<2.5) -> Green
        r4 = Rule(user_id='demo_user', name='Company Price Rule', label='Green', priority=5, active=True)
        db.session.add(r4); db.session.flush()
        db.session.add(RuleCondition(rule_id=r4.id, group_id=1, key_path='CompanyName', operator='=', value_json='"Google"'))
        db.session.add(RuleCondition(rule_id=r4.id, group_id=2, key_path='CompanyName', operator='=', value_json='"Amazon"'))
        db.session.add(RuleCondition(rule_id=r4.id, group_id=2, key_path='Price', operator='<', value_json='2.5'))

        db.session.commit()
