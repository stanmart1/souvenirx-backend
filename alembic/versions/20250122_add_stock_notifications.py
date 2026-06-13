"""add_stock_notifications_and_email_campaigns

Revision ID: 20250122_add_stock_notifications
Revises: 20250121_add_email_verification_and_settings
Create Date: 2025-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250122_add_stock_notifications'
down_revision = '20250121_add_email_verification_and_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── stock_notifications ──────────────────────────────────────────────────
    op.create_table(
        'stock_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('guest_email', sa.String(length=255), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_notified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_stock_notification_user_product'),
    )
    op.create_index('ix_stock_notifications_product_id', 'stock_notifications', ['product_id'])
    op.create_index('ix_stock_notifications_guest_email', 'stock_notifications', ['guest_email'])

    # ── email_campaigns ──────────────────────────────────────────────────────
    op.create_table(
        'email_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('target_audience', sa.String(length=50), nullable=False, server_default=sa.text("'all'")),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('opened_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── campaign_recipients ──────────────────────────────────────────────────
    op.create_table(
        'campaign_recipients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['email_campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaign_recipients_campaign_id', 'campaign_recipients', ['campaign_id'])
    op.create_index('ix_campaign_recipients_email', 'campaign_recipients', ['email'])


def downgrade() -> None:
    # Drop in reverse order
    op.drop_index('ix_campaign_recipients_email', 'campaign_recipients')
    op.drop_index('ix_campaign_recipients_campaign_id', 'campaign_recipients')
    op.drop_table('campaign_recipients')

    op.drop_table('email_campaigns')

    op.drop_index('ix_stock_notifications_guest_email', 'stock_notifications')
    op.drop_index('ix_stock_notifications_product_id', 'stock_notifications')
    op.drop_table('stock_notifications')
