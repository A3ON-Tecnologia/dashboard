from flask import Blueprint, render_template, jsonify, abort
from flask_login import login_required, current_user
from app.models.user import User, db
from app.services.theme_service import get_current_theme


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

