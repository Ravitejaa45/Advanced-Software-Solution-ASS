import json
import pytest
from app import create_app, db

@pytest.fixture
def client():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
    })
    with app.app_context():
        db.create_all()
    client = app.test_client()
    yield client

def test_rules_crud(client):
    # Create
    rule = {
        "name":"Test", "label":"Green","priority":5,"active":True,
        "conditions":[{"group":1,"key_path":"Price","operator":"<","value":2}]
    }
    rv = client.post("/api/rules", json=rule, headers={"X-User-Id":"u1"})
    assert rv.status_code == 201
    rid = rv.get_json()["id"]

    # List
    rv = client.get("/api/rules", headers={"X-User-Id":"u1"})
    data = rv.get_json()
    assert len(data) == 1 and data[0]["id"] == rid

    # Toggle
    rv = client.post(f"/api/rules/{rid}/toggle", headers={"X-User-Id":"u1"})
    assert rv.status_code == 200

    # Update
    rv = client.put(f"/api/rules/{rid}", json={"label":"Yellow"}, headers={"X-User-Id":"u1"})
    assert rv.status_code == 200

    # Delete
    rv = client.delete(f"/api/rules/{rid}", headers={"X-User-Id":"u1"})
    assert rv.status_code == 200

def test_process_and_stats(client):
    # Create a rule
    client.post("/api/rules", json={
        "name":"Choco <2", "label":"Green","priority":10,"active":True,
        "conditions":[
            {"group":1,"key_path":"Product","operator":"=","value":"Chocolate"},
            {"group":1,"key_path":"Price","operator":"<","value":2}
        ]
    }, headers={"X-User-Id":"u1"})

    # Process payload -> should match
    rv = client.post("/api/process", json={"Product":"Chocolate","Price":1.5}, headers={"X-User-Id":"u1"})
    assert rv.status_code == 200
    res = rv.get_json()
    assert "Green" in res["labels"]

    # Stats
    rv = client.get("/api/statistics", headers={"X-User-Id":"u1"})
    assert rv.status_code == 200
    stats = rv.get_json()
    assert stats["total_payloads"] == 1
