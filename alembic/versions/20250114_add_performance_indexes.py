"""Add performance indexes for product queries

Revision ID: 20250114_add_performance_indexes
Revises: 20250113_add_homepage_content
Create Date: 2025-01-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250114_add_performance_indexes'
down_revision = '20250113_add_homepage_content'
branch_labels = None
depends_on = None


def upgrade():
    # Composite index for category + active + stock filtering
    op.create_index(
        'idx_products_category_active_stock',
        'products',
        ['category_id', 'is_active', 'stock'],
        unique=False
    )
    
    # Composite index for rating + active (popular products)
    op.create_index(
        'idx_products_rating_active',
        'products',
        ['rating', 'is_active'],
        unique=False
    )
    
    # Composite index for price range queries
    op.create_index(
        'idx_products_price_range',
        'products',
        ['base_price', 'is_active'],
        unique=False
    )
    
    # Index for reviews_count for sorting
    op.create_index(
        'idx_products_reviews_count',
        'products',
        ['reviews_count', 'is_active'],
        unique=False
    )
    
    # Index for variant lookups
    op.create_index(
        'idx_product_variants_product_id',
        'product_variants',
        ['product_id', 'is_active'],
        unique=False
    )
    
    # Index for grouped products
    op.create_index(
        'idx_products_product_group',
        'products',
        ['product_group_id', 'is_active'],
        unique=False
    )
    
    # Index for delivery zone state lookup
    op.create_index(
        'idx_delivery_zones_states',
        'delivery_zones',
        ['states'],
        unique=False,
        postgresql_using='gin'
    )
    
    # Index for delivery zone LGA lookup
    op.create_index(
        'idx_delivery_zones_lgas',
        'delivery_zones',
        ['lgas'],
        unique=False,
        postgresql_using='gin'
    )
    
    # Index for product tiers lookup
    op.create_index(
        'idx_product_tiers_product_id',
        'product_tiers',
        ['product_id', 'min_qty'],
        unique=False
    )


def downgrade():
    op.drop_index('idx_product_tiers_product_id', 'product_tiers')
    op.drop_index('idx_delivery_zones_lgas', 'delivery_zones', postgresql_using='gin')
    op.drop_index('idx_products_product_group', 'products')
    op.drop_index('idx_product_variants_product_id', 'product_variants')
    op.drop_index('idx_products_reviews_count', 'products')
    op.drop_index('idx_products_price_range', 'products')
    op.drop_index('idx_products_rating_active', 'products')
    op.drop_index('idx_products_category_active_stock', 'products')
