"""Atualiza tipos de workflow e cria analise_uploads

Revision ID: b0c1d2e3f4a5
Revises: create_workflows_table
Create Date: 2025-10-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'b0c1d2e3f4a5'
down_revision = 'create_workflows_table'
branch_labels = None
depends_on = None


NEW_WORKFLOW_ENUM = mysql.ENUM('balancete', 'analise_jp', name='workflow_tipo')
OLD_WORKFLOW_ENUM = mysql.ENUM('comparativo', 'evolucao', name='workflow_tipo')


def upgrade():
    # Ajusta a coluna tipo para receber os novos valores
    op.alter_column(
        'workflows',
        'tipo',
        existing_type=OLD_WORKFLOW_ENUM,
        type_=sa.String(length=50),
        existing_nullable=False
    )

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE workflows SET tipo = 'balancete' WHERE tipo IN ('comparativo', 'evolucao')"))

    op.alter_column(
        'workflows',
        'tipo',
        existing_type=sa.String(length=50),
        type_=NEW_WORKFLOW_ENUM,
        existing_nullable=False
    )

    op.create_table(
        'analise_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('categoria', sa.String(length=120), nullable=False),
        sa.Column('nome_arquivo', sa.String(length=255), nullable=False),
        sa.Column('caminho_arquivo', sa.String(length=500), nullable=False),
        sa.Column('dados_extraidos', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('analise_uploads')

    op.alter_column(
        'workflows',
        'tipo',
        existing_type=NEW_WORKFLOW_ENUM,
        type_=sa.String(length=50),
        existing_nullable=False
    )

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE workflows SET tipo = 'comparativo' WHERE tipo = 'balancete'"))
    connection.execute(sa.text("UPDATE workflows SET tipo = 'evolucao' WHERE tipo = 'analise_jp'"))

    op.alter_column(
        'workflows',
        'tipo',
        existing_type=sa.String(length=50),
        type_=OLD_WORKFLOW_ENUM,
        existing_nullable=False
    )
