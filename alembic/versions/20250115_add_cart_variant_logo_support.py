"""Add variant and logo support to cart items

Revision ID: 20250115_add_cart_variant_logo_support
Revises: 20250114_add_performance_indexes
Create Date: 2025-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250115_add_cart_variant_logo_support'
down_revision: Union[str, None] = '20250114_add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add variant_id column to cart_items
    op.add_column('cart_items', sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint for variant_id
    op.create_foreign_key(
        'fk_cart_items_variant_id',
        'cart_items', 'product_variants',
        ['variant_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add logo_url column to cart_items
    op.add_column('cart_items', sa.Column('logo_url', sa.String(length=500), nullable=True))
    
    # Add created_at column to cart_items (for analytics)
    op.add_column('cart_items', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    
    # Create index for variant_id lookups
    op.create_index(
        'idx_cart_items_variant_id',
        'cart_items',
        ['variant_id'],
        unique=False
    )
    
    # Create index for created_at (for abandoned cart analytics)
    op.create_index(
        'idx_cart_items_created_at',
        'cart_items',
        ['created_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_cart_items_created_at', 'cart_items')
    op.drop_index('idx_cart_items_variant_id', 'cart_items')
    
    # Drop columns
    op.drop_column('cart_items', 'created_at')
    op.drop_column('cart_items', 'logo_url')
    op.drop_constraint('fk_cart_items_variant_id', 'cart_items', type_='foreignkey')
    op.drop_column('cart_items', 'variant_id')
