"""add promo analytics and stackable fields

Revision ID: 20260118_add_promo_analytics
Revises: 20260118_add_tags
Create Date: 2026-01-18 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func

# revision identifiers, used by Alembic.
revision = '20260118_add_promo_analytics'
down_revision = '20260118_add_tags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('promo_codes', sa.Column('total_revenue_impact', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('promo_codes', sa.Column('is_stackable', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('promo_codes', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()))


def downgrade() -> None:
    op.drop_column('promo_codes', 'created_at')
    op.drop_column('promo_codes', 'is_stackable')
    op.drop_column('promo_codes', 'total_revenue_impact')
