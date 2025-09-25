import click
from app import create_app
from app.models.user import db, User
from app.services.auth_service import bcrypt

app = create_app()

@app.cli.command("create-admin")
@click.argument("nome")
@click.argument("email")
@click.argument("password")
def create_admin(nome, email, password):
    """Cria um novo usuário administrador."""
    if User.query.filter_by(email=email).first():
        print(f"Erro: O email '{email}' já está em uso.")
        return

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    admin_user = User(
        nome=nome,
        email=email,
        senha_hash=hashed_password,
        admin=True
    )
    db.session.add(admin_user)
    db.session.commit()
    print(f"Usuário administrador '{nome}' criado com sucesso.")

if __name__ == '__main__':
    app.run(debug=True, port=8000)
