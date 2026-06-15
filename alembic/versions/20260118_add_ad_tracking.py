"""add ad tracking and ab testing

Revision ID: 20260118_add_ad_tracking
Revises: 20260118_add_bank_verification
Create Date: 2026-01-18 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260118_add_ad_tracking'
down_revision = '20260118_add_bank_verification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('ads', sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ads', sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ads', sa.Column('variant', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('ads', 'variant')
    op.drop_column('ads', 'clicks')
    op.drop_column('ads', 'impressions')
