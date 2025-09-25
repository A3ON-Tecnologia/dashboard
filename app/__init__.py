import os
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from app.models.user import db, User
from app.services.auth_service import init_bcrypt

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
    
    print(f"Template directory: {template_dir}")
    print(f"Static directory: {static_dir}")
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    app.config.from_object(Config)
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    init_bcrypt(app)
    
    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    with app.app_context():
        # Register blueprints
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        
        
        return app
