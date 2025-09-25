# Dashboard Futurista com Temas Dinâmicos

Sistema moderno de dashboard com autenticação e suporte a múltiplos temas visuais, desenvolvido com Flask e TailwindCSS.

## Tecnologias Utilizadas

- **Backend**: Python + Flask
- **Frontend**: HTML + TailwindCSS + JavaScript
- **Banco de Dados**: MySQL
- **Autenticação**: Flask-Login + Bcrypt
- **Temas**: Sistema próprio de temas com Tailwind

## Funcionalidades

- Sistema de autenticação completo (login/cadastro)
- Temas visuais dinâmicos:
  - Dark (fundo escuro, cores sóbrias)
  - Light (fundo claro, cores suaves)
  - Neon (cores vibrantes, efeito glow)
  - Futurist (azul/roxo com gradientes)
  - Classic (estilo clean corporativo)
- Mudança de tema em tempo real
- Persistência do tema escolhido
- Interface responsiva

## Configuração do Ambiente

1. Clone o repositório
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure o banco de dados:
   - Crie um banco MySQL chamado `cadastro_empresas`
   - Usuário: root
   - Sem senha
   
5. Configure o arquivo .env:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=sua_chave_secreta
   DATABASE_URL=mysql://root:@localhost/cadastro_empresas
   ```

## Executando o Projeto

1. Ative o ambiente virtual:
   ```bash
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

2. Execute a aplicação:
   ```bash
   python run.py
   ```

3. Acesse http://localhost:5000 no navegador

## Uso do Sistema

1. **Página Inicial**
   - Acesse a home page
   - Escolha entre Login ou Cadastro

2. **Cadastro**
   - Clique em "Cadastro"
   - Preencha nome, email e senha
   - Submeta o formulário

3. **Login**
   - Clique em "Login"
   - Insira email e senha
   - Acesse o sistema

4. **Dashboard**
   - Após login, você será redirecionado ao dashboard
   - Use o dropdown de temas na navbar para mudar o visual
   - O tema escolhido será salvo para futuras sessões

5. **Mudança de Tema**
   - Clique no botão "Temas" na navbar
   - Selecione um dos 5 temas disponíveis
   - A mudança é instantânea e persiste entre sessões

6. **Logout**
   - Clique em "Sair" na navbar
   - Você será redirecionado para a home

## Estrutura do Projeto

```
/project_root
│── /app
│   │── __init__.py
│   │── /models
│   │   └── user.py
│   │── /routes
│   │   │── auth.py
│   │   └── main.py
│   │── /services
│   │   │── auth_service.py
│   │   └── theme_service.py
│   │── /themes
│   │   └── theme_config.py
│   │── /templates
│   │   │── base.html
│   │   │── home.html
│   │   └── dashboard.html
│   └── /static
│── config.py
│── run.py
│── requirements.txt
│── .env.example
└── README.md
```

## Próximas Etapas

- Implementação dos dashboards
- Importação de dados CSV
- Gráficos interativos
- Relatórios personalizados
- Mais temas visuais
