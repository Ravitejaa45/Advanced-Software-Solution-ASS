import argparse
from app import create_app, db
from app.models import seed_demo_data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initdb', action='store_true', help='Create DB tables')
    parser.add_argument('--loaddemo', action='store_true', help='Load demo rules')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.initdb:
            db.create_all()
            print("DB initialized.")
        if args.loaddemo:
            seed_demo_data()
            print("Loaded demo rules.")
    app.run(debug=True)

if __name__ == "__main__":
    main()