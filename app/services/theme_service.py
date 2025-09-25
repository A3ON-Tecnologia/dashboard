from flask import session
from flask_login import current_user
from app.models.user import db
from app.themes.theme_config import get_theme

def get_current_theme():
    return get_theme(session.get('theme', 'futurist'))

def update_user_theme(theme_name):
    session['theme'] = theme_name
    return get_theme(theme_name)
