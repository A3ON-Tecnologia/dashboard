from flask import Blueprint, request, jsonify, render_template
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import register_user, validate_login, update_user_profile
from app.services.theme_service import get_current_theme

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    password = data.get('password')
    
    if not all([nome, email, password]):
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
    
    try:
        user = register_user(nome, email, password)
        login_user(user)
        return jsonify({'message': 'Cadastro realizado com sucesso!'}), 201
    except Exception as e:
        return jsonify({'error': 'Email já cadastrado'}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400
    
    user = validate_login(email, password)
    if user:
        login_user(user)
        return jsonify({'message': 'Login realizado com sucesso!'}), 200
    return jsonify({'error': 'Email ou senha inválidos'}), 401

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout realizado com sucesso!'}), 200

@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    password = data.get('password')

    if not nome or not email:
        return jsonify({'error': 'Nome e email são obrigatórios'}), 400

    try:
        update_user_profile(current_user, nome, email, password)
        return jsonify({'message': 'Perfil atualizado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
