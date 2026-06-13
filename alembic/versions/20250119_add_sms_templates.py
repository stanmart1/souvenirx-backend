"""Add SMS templates table

Revision ID: 20250119_add_sms_templates
Revises: 20250118_add_cart_recovery
Create Date: 2025-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250119_add_sms_templates'
down_revision: Union[str, None] = '20250118_add_cart_recovery'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sms_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create indexes
    op.create_index('idx_sms_templates_name', 'sms_templates', ['name'], unique=False)
    op.create_index('idx_sms_templates_is_active', 'sms_templates', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_sms_templates_is_active', 'sms_templates')
    op.drop_index('idx_sms_templates_name', 'sms_templates')
    op.drop_table('sms_templates')
