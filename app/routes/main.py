from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.services.theme_service import get_current_theme, update_user_theme

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    theme = get_current_theme()
    return render_template('home.html', theme=theme)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    theme = get_current_theme()
    return render_template('dashboard.html', theme=theme)

@main_bp.route('/theme/<theme_name>', methods=['POST'])
def change_theme(theme_name):
    theme = update_user_theme(theme_name)
    return jsonify({'message': 'Tema atualizado com sucesso!', 'theme': theme})
