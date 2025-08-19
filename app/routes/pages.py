from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def config_page():
    return render_template('config.html')

@pages_bp.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')
