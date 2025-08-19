import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(app.instance_path, 'ass.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SWAGGER'] = {'title': 'ASS Data Labeling API', 'uiversion': 3}

    db.init_app(app)
    Swagger(app)

    from .routes.api import api_bp
    from .routes.pages import pages_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(pages_bp)
    return app
