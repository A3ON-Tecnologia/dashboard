from flask_bcrypt import Bcrypt
from app.models.user import User, db

bcrypt = Bcrypt()

def init_bcrypt(app):
    bcrypt.init_app(app)

def register_user(nome, email, password):
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(nome=nome, email=email, senha_hash=hashed_password)
    db.session.add(user)
    db.session.commit()
    return user

def validate_login(email, password):
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.senha_hash, password):
        return user
    return None
