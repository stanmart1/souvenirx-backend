"""Add saved payment methods table

Revision ID: 20250108_add_payment_methods
Revises: 20250107_add_newsletter_subscribers
Create Date: 2025-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250108_add_payment_methods'
down_revision = '20250107_add_newsletter_subscribers'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'saved_payment_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_token', sa.String(255), nullable=False),
        sa.Column('payment_gateway', sa.String(50), nullable=False),
        sa.Column('card_last4', sa.String(4), nullable=False),
        sa.Column('card_brand', sa.String(20), nullable=False),
        sa.Column('expiry_month', sa.Integer(), nullable=False),
        sa.Column('expiry_year', sa.Integer(), nullable=False),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_saved_payment_methods_user_id', 'saved_payment_methods', ['user_id'])
    op.create_foreign_key('fk_payment_methods_user', 'saved_payment_methods', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('fk_payment_methods_user', 'saved_payment_methods', type_='foreignkey')
    op.drop_index('ix_saved_payment_methods_user_id', table_name='saved_payment_methods')
    op.drop_table('saved_payment_methods')
