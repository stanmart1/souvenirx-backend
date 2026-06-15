"""add bank verification fields

Revision ID: 20260118_add_bank_verification
Revises: 20260118_add_promo_analytics
Create Date: 2026-01-18 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260118_add_bank_verification'
down_revision = '20260118_add_promo_analytics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('bank_accounts', sa.Column('bank_code', sa.String(length=10), nullable=True))
    op.add_column('bank_accounts', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('bank_accounts', 'is_verified')
    op.drop_column('bank_accounts', 'bank_code')
