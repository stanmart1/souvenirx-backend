"""add_email_verification_and_settings

Revision ID: 20250121_add_email_verification_and_settings
Revises: 20250120_add_affiliate_bank_details
Create Date: 2025-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250121_add_email_verification_and_settings'
down_revision = '20250120_add_affiliate_bank_details'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email verification fields to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('verification_token', sa.String(length=255), nullable=True))
    
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index('ix_system_settings_key', 'system_settings', ['key'])
    
    # Insert default settings
    op.execute("""
        INSERT INTO system_settings (key, value, description) VALUES
        ('affiliate_auto_approve', 'false', 'Auto-approve affiliate registrations without admin review'),
        ('affiliate_require_email_verification', 'true', 'Require email verification before affiliates can access dashboard'),
        ('min_payout_amount', '500000', 'Minimum payout amount in kobo (₦5,000)'),
        ('commission_rate', '0.10', 'Default commission rate (10%)')
    """)


def downgrade() -> None:
    # Remove email verification fields
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'email_verified')
    
    # Drop system_settings table
    op.drop_index('ix_system_settings_key', 'system_settings')
    op.drop_table('system_settings')
