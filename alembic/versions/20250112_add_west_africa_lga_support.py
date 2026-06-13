"""Add West Africa and LGA support to delivery zones

Revision ID: 20250112_add_west_africa_lga_support
Revises: 20250111_add_shipping_automation
Create Date: 2025-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250112_add_west_africa_lga_support'
down_revision = '20250111_add_shipping_automation'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns for hierarchical geography
    op.add_column('delivery_zones', sa.Column('countries', postgresql.JSONB(), nullable=False, server_default='["Nigeria"]'))
    op.add_column('delivery_zones', sa.Column('lgas', postgresql.JSONB(), default=list))
    op.add_column('delivery_zones', sa.Column('zone_type', sa.String(20), default='state'))
    
    # Add columns for international shipping
    op.add_column('delivery_zones', sa.Column('is_international', sa.Boolean(), default=False))
    op.add_column('delivery_zones', sa.Column('customs_handling_fee', sa.Integer(), default=0))
    op.add_column('delivery_zones', sa.Column('border_crossing_fee', sa.Integer(), default=0))


def downgrade():
    op.drop_column('delivery_zones', 'border_crossing_fee')
    op.drop_column('delivery_zones', 'customs_handling_fee')
    op.drop_column('delivery_zones', 'is_international')
    op.drop_column('delivery_zones', 'zone_type')
    op.drop_column('delivery_zones', 'lgas')
    op.drop_column('delivery_zones', 'countries')
