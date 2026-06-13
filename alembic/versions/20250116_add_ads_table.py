"""Add ads table for homepage advertisements

Revision ID: 20250116_add_ads_table
Revises: 20250115_add_cart_variant_logo_support
Create Date: 2025-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250116_add_ads_table'
down_revision: Union[str, None] = '20250115_add_cart_variant_logo_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('mobile_image_url', sa.String(length=500), nullable=True),
        sa.Column('link_url', sa.String(length=500), nullable=True),
        sa.Column('position', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_ads_position', 'ads', ['position'], unique=False)
    op.create_index('idx_ads_is_active', 'ads', ['is_active'], unique=False)
    op.create_index('idx_ads_date_range', 'ads', ['start_date', 'end_date'], unique=False)
    op.create_index('idx_ads_sort_order', 'ads', ['sort_order'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_ads_sort_order', 'ads')
    op.drop_index('idx_ads_date_range', 'ads')
    op.drop_index('idx_ads_is_active', 'ads')
    op.drop_index('idx_ads_position', 'ads')
    op.drop_table('ads')
