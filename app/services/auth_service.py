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

def update_user_profile(user, nome, email, password=None):
    # Verifica se o novo email já está em uso por outro usuário
    if email != user.email and User.query.filter_by(email=email).first():
        raise Exception('Este email já está em uso por outra conta.')

    user.nome = nome
    user.email = email

    if password:
        user.senha_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    db.session.commit()
