# Dashboard Futurista com Temas Dinamicos

Aplicacao Flask que oferece um dashboard moderno com autenticacao, troca de temas e integracao com MySQL.

## Tecnologias

- Flask
- TailwindCSS
- MySQL

## Requisitos

- Python 3.10.x (64 bits)
- Pip na mesma versao do Python
- Servidor MySQL 8.x acessivel localmente

## Como preparar o ambiente


1. **Clonar o repositorio**
   ```bash
   git clone <URL_DO_REPO>
   cd dashboards
   ```
2. **Criar e ativar um ambiente virtual**
   - Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\\venv\\Scripts\\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. **Instalar as dependencias Python**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Configurar o banco MySQL**
   ```sql
   CREATE DATABASE dashboards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
   Ajuste usuario e senha conforme a sua instalacao.
5. **Criar o arquivo `.env`** (copie do exemplo caso exista):
   ```bash
   cp .env.example .env  # Linux/macOS
   copy .env.example .env  # Windows
   ```
   Edite o arquivo `.env` para refletir suas credenciais:
   ```ini
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=uma_chave_segura
   DATABASE_URL=mysql+mysqlconnector://<usuario>:<senha>@localhost/dashboards
   ```
6. **Aplicar as migracoes**
   ```bash
   flask db upgrade
   ```
   No Windows PowerShell:
   ```powershell
   $env:FLASK_APP = "run.py"
   flask db upgrade
   ```

## Executando na porta 8000

1. Certifique-se de que o ambiente virtual esta ativo e o arquivo `.env` configurado.
2. Inicie a aplicacao diretamente com o script principal, que ja define a porta 8000:
   ```bash
   python run.py
   ```
3. Acesse o dashboard em `http://localhost:8000`.

Se preferir usar `flask run`, defina a porta manualmente:
```bash
export FLASK_APP=run.py      # Linux/macOS
set FLASK_APP=run.py         # Windows CMD
$env:FLASK_APP = "run.py"    # Windows PowerShell
flask run --port 8000
```

## Notas adicionais

- Utilize `flask db migrate` e `flask db upgrade` sempre que criar novos modelos.
- Para criar um usuario administrador execute:
  ```bash
  flask create-admin "Nome" email@example.com senha123
  ```
- Ative o ambiente virtual sempre que for trabalhar no projeto.
