"""Add email templates table for customizable email communications

Revision ID: 20250117_add_email_templates
Revises: 20250116_add_ads_table
Create Date: 2025-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250117_add_email_templates'
down_revision: Union[str, None] = '20250116_add_ads_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create indexes
    op.create_index('idx_email_templates_name', 'email_templates', ['name'], unique=False)
    op.create_index('idx_email_templates_is_active', 'email_templates', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_email_templates_is_active', 'email_templates')
    op.drop_index('idx_email_templates_name', 'email_templates')
    op.drop_table('email_templates')
