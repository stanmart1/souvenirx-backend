"""add_affiliate_bank_details

Revision ID: 20250120_add_affiliate_bank_details
Revises: 20250119_add_sms_templates
Create Date: 2025-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250120_add_affiliate_bank_details'
down_revision = '20250119_add_sms_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add bank details columns to affiliates table
    op.add_column('affiliates', sa.Column('bank_name', sa.String(length=100), nullable=True))
    op.add_column('affiliates', sa.Column('account_number', sa.String(length=20), nullable=True))
    op.add_column('affiliates', sa.Column('account_name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove bank details columns
    op.drop_column('affiliates', 'account_name')
    op.drop_column('affiliates', 'account_number')
    op.drop_column('affiliates', 'bank_name')
