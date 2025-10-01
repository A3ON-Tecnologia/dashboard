"""Add hidden rows support to analise_uploads

Revision ID: 1a2b3c4d5e6f
Revises: b0c1d2e3f4a5
Create Date: 2024-05-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect



# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = 'b0c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_columns = {column['name'] for column in inspector.get_columns('analise_uploads')}
    if 'linhas_ocultas' in existing_columns:
        return

    json_type = sa.JSON()
    if bind.dialect.name == 'sqlite':
        json_type = sa.JSON().with_variant(sa.Text(), 'sqlite')

    op.add_column('analise_uploads', sa.Column('linhas_ocultas', json_type, nullable=True))

    if bind.dialect.name == 'mysql':
        op.execute(sa.text('UPDATE analise_uploads SET linhas_ocultas = JSON_ARRAY()'))
    elif bind.dialect.name == 'postgresql':
        op.execute(sa.text("UPDATE analise_uploads SET linhas_ocultas = '[]'::json"))
    else:
        op.execute(sa.text("UPDATE analise_uploads SET linhas_ocultas = '[]'"))

    op.alter_column(
        'analise_uploads',
        'linhas_ocultas',
        existing_type=json_type,
        nullable=False,
    op.add_column(
        'analise_uploads',
        sa.Column('linhas_ocultas', sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
    )
    op.alter_column(
        'analise_uploads',
        'linhas_ocultas',
        server_default=None
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column['name'] for column in inspector.get_columns('analise_uploads')}

    if 'linhas_ocultas' in existing_columns:
        op.drop_column('analise_uploads', 'linhas_ocultas')
    op.drop_column('analise_uploads', 'linhas_ocultas')
