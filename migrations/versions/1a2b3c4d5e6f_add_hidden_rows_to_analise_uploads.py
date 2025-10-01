"""Add hidden rows support to analise_uploads

Revision ID: 1a2b3c4d5e6f
Revises: b0c1d2e3f4a5
Create Date: 2024-05-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = 'b0c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade():
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
    op.drop_column('analise_uploads', 'linhas_ocultas')
