import os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from app.models.user import db, User
from app.models.dashboard import Dashboard
from app.models.analise_jp_chart import AnaliseJPChart
from app.models.workflow import Workflow
from app.services.auth_service import init_bcrypt

login_manager = LoginManager()

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc


def to_sao_paulo(dt, fmt="%d/%m/%Y %H:%M"):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(SAO_PAULO_TZ).strftime(fmt)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

    print(f"Template directory: {template_dir}")
    print(f"Static directory: {static_dir}")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )

    app.config.from_object(Config)
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.filters['datetime_sp'] = to_sao_paulo

    upload_path = Path(app.config['UPLOAD_FOLDER'])
    upload_path.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    init_bcrypt(app)

    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # Importar e registrar blueprints
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.admin import admin_bp
        from app.routes.workflow import workflow_bp
        from app.routes.analise_jp import analise_jp_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(workflow_bp)
        app.register_blueprint(analise_jp_bp)

        return app
