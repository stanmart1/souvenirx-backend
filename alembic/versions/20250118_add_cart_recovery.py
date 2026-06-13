"""Add cart recovery tracking table

Revision ID: 20250118_add_cart_recovery
Revises: 20250117_add_email_templates
Create Date: 2025-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20250118_add_cart_recovery'
down_revision: Union[str, None] = '20250117_add_email_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cart_recovery',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('sms_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovery_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_recovery_attempt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_cart_recovery_user_id', 'cart_recovery', ['user_id'], unique=False)
    op.create_index('idx_cart_recovery_email_sent_at', 'cart_recovery', ['email_sent_at'], unique=False)
    op.create_index('idx_cart_recovery_last_recovery', 'cart_recovery', ['last_recovery_attempt'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_cart_recovery_last_recovery', 'cart_recovery')
    op.drop_index('idx_cart_recovery_email_sent_at', 'cart_recovery')
    op.drop_index('idx_cart_recovery_user_id', 'cart_recovery')
    op.drop_table('cart_recovery')
