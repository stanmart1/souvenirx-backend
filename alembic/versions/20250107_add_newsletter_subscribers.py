"""Add newsletter subscribers table

Revision ID: 20250107_add_newsletter_subscribers
Revises: 20250106_add_testimonials_table
Create Date: 2025-01-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250107_add_newsletter_subscribers'
down_revision = '20250106_add_testimonials_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'newsletter_subscribers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('is_subscribed', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_newsletter_subscribers_email', 'newsletter_subscribers', ['email'])


def downgrade():
    op.drop_index('ix_newsletter_subscribers_email', table_name='newsletter_subscribers')
    op.drop_table('newsletter_subscribers')
