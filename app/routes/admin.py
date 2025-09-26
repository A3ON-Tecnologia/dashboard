from flask import Blueprint, render_template, jsonify, abort, request
from flask_login import login_required, current_user
from app.models.user import User, db
from app.services.theme_service import get_current_theme
from werkzeug.security import generate_password_hash


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _ensure_admin():
    if not current_user.is_authenticated or not getattr(current_user, 'admin', False):
        abort(403)


@admin_bp.route('/users')
@login_required
def list_users():
    _ensure_admin()
    users = User.query.order_by(User.id.asc()).all()
    theme = get_current_theme()
    return render_template('admin_users.html', theme=theme, users=users)


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    _ensure_admin()
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'nome': user.nome,
        'email': user.email,
        'admin': user.admin,
        'data_criacao': user.data_criacao.isoformat() if user.data_criacao else None
    })


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    _ensure_admin()
    user = User.query.get_or_404(user_id)
    
    data = request.get_json()
    
    # Atualizar campos básicos
    if 'nome' in data:
        user.nome = data['nome']
    if 'email' in data:
        user.email = data['email']
    
    # Atualizar senha se fornecida
    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])
    
    try:
        db.session.commit()
        return jsonify({'message': 'Usuário atualizado com sucesso.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar usuário.'}), 500


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@login_required
def update_user_role(user_id):
    _ensure_admin()
    if current_user.id == user_id:
        return jsonify({'error': 'Você não pode alterar seu próprio tipo de usuário.'}), 400

    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'admin' not in data:
        return jsonify({'error': 'Campo admin é obrigatório.'}), 400
    
    user.admin = bool(data['admin'])
    
    try:
        db.session.commit()
        action = 'promovido a admin' if user.admin else 'removido dos admins'
        return jsonify({'message': f'Usuário {action} com sucesso.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao alterar tipo de usuário.'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    _ensure_admin()
    if current_user.id == user_id:
        return jsonify({'error': 'Você não pode excluir a si mesmo.'}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Usuário excluído com sucesso.'})

