"""add product is_archived field

Revision ID: 20260118_add_archived
Revises: 20260617_add_review_moderation_fields
Create Date: 2026-01-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260118_add_archived'
down_revision = '20260617_add_review_moderation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_archived column to products table
    op.add_column('products', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_products_is_archived'), 'products', ['is_archived'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_products_is_archived'), table_name='products')
    op.drop_column('products', 'is_archived')
