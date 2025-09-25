from flask import session
from flask_login import current_user
from app.models.user import db
from app.themes.theme_config import get_theme

def get_current_theme():
    if current_user.is_authenticated:
        return get_theme(current_user.tema_preferido)
    return get_theme(session.get('theme', 'futurist'))

def update_user_theme(theme_name):
    if current_user.is_authenticated:
        current_user.tema_preferido = theme_name
        db.session.commit()
    session['theme'] = theme_name
    return get_theme(theme_name)
