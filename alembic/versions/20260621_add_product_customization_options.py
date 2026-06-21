"""Add product customization_options

Revision ID: 20260621_add_product_customization_options
Revises: 20260620_merge_heads
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260621_add_product_customization_options'
down_revision = '20260620_merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('customization_options', postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column('products', 'customization_options')
