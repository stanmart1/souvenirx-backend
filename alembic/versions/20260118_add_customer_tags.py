"""add customer tags field

Revision ID: 20260118_add_tags
Revises: 20260118_add_notes
Create Date: 2026-01-18 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260118_add_tags'
down_revision = '20260118_add_notes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('tags', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'tags')
