"""Add loyalty system tables

Revision ID: 20260620_loyalty_system
Revises: 20260620_user_avatar_loyalty
Create Date: 2026-06-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260620_loyalty_system'
down_revision = '20260620_user_avatar_loyalty'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'loyalty_transactions' not in existing_tables:
        op.create_table(
            'loyalty_transactions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('points', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('description', sa.String(500), nullable=False),
            sa.Column('order_number', sa.String(100), nullable=True),
            sa.Column('reference_id', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_loyalty_transactions_user_id', 'loyalty_transactions', ['user_id'])
        op.create_index('ix_loyalty_transactions_type', 'loyalty_transactions', ['type'])

    if 'loyalty_rules' not in existing_tables:
        op.create_table(
            'loyalty_rules',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('type', sa.String(50), nullable=False, unique=True),
            sa.Column('value', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('description', sa.String(500), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

        op.bulk_insert(
            sa.table(
                'loyalty_rules',
                sa.column('name', sa.String()),
                sa.column('type', sa.String()),
                sa.column('value', sa.Integer()),
                sa.column('is_active', sa.Boolean()),
                sa.column('description', sa.String()),
            ),
            [
                {
                    'name': 'Signup Bonus',
                    'type': 'signup_bonus',
                    'value': 100,
                    'is_active': True,
                    'description': 'Points awarded when a new user registers',
                },
                {
                    'name': 'Earn per Kobo',
                    'type': 'earn_per_kobo',
                    'value': 10000,
                    'is_active': True,
                    'description': 'Points earned per N100 spent (1 point per N100)',
                },
                {
                    'name': 'Referral Bonus',
                    'type': 'referral_bonus',
                    'value': 50,
                    'is_active': True,
                    'description': 'Points awarded for each successful referral',
                },
                {
                    'name': 'Review Bonus',
                    'type': 'review_bonus',
                    'value': 25,
                    'is_active': True,
                    'description': 'Points awarded for leaving a product review',
                },
                {
                    'name': 'Redeem Rate',
                    'type': 'redeem_rate',
                    'value': 10,
                    'is_active': True,
                    'description': 'Points needed to redeem N1 (10 points = N1)',
                },
            ],
        )


def downgrade() -> None:
    op.drop_table('loyalty_rules')
    op.drop_table('loyalty_transactions')
