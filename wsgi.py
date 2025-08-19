from app import create_app, db
from app.models import seed_demo_data
import os

app = create_app()

with app.app_context():
    db.create_all()
    if os.environ.get("SEED_DEMO", "false").lower() in {"1","true","yes"}:
        seed_demo_data()