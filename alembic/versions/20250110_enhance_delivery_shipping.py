"""Enhance delivery zones and add shipping methods

Revision ID: 20250110_enhance_delivery_shipping
Revises: 20250109_add_product_groups_variants
Create Date: 2025-01-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250110_enhance_delivery_shipping'
down_revision = '20250109_add_product_groups_variants'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to delivery_zones
    op.add_column('delivery_zones', sa.Column('states', postgresql.JSONB(), nullable=False, server_default='[]'))
    op.add_column('delivery_zones', sa.Column('free_shipping_threshold', sa.Integer(), default=0))
    op.add_column('delivery_zones', sa.Column('weight_fee_per_kg', sa.Integer(), default=0))
    op.add_column('delivery_zones', sa.Column('volume_fee_per_unit', sa.Integer(), default=0))
    op.add_column('delivery_zones', sa.Column('min_days', sa.Integer(), default=3))
    op.add_column('delivery_zones', sa.Column('max_days', sa.Integer(), default=7))
    
    # Create shipping_methods table
    op.create_table(
        'shipping_methods',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('base_fee', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('free_above_amount', sa.Integer(), default=0),
        sa.Column('fee_per_kg', sa.Integer(), default=0),
        sa.Column('fee_per_item', sa.Integer(), default=0),
        sa.Column('min_days', sa.Integer(), default=3),
        sa.Column('max_days', sa.Integer(), default=7),
    )


def downgrade():
    op.drop_table('shipping_methods')
    op.drop_column('delivery_zones', 'max_days')
    op.drop_column('delivery_zones', 'min_days')
    op.drop_column('delivery_zones', 'volume_fee_per_unit')
    op.drop_column('delivery_zones', 'weight_fee_per_kg')
    op.drop_column('delivery_zones', 'free_shipping_threshold')
    op.drop_column('delivery_zones', 'states')
