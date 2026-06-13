"""Add shipping automation features

Revision ID: 20250111_add_shipping_automation
Revises: 20250110_enhance_delivery_shipping
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250111_add_shipping_automation'
down_revision = '20250110_enhance_delivery_shipping'
branch_labels = None
depends_on = None


def upgrade():
    # Add automation columns to delivery_zones
    op.add_column('delivery_zones', sa.Column('default_carrier', sa.String(50), nullable=True))
    op.add_column('delivery_zones', sa.Column('auto_assign', sa.Boolean(), default=True))
    
    # Add automation columns to shipping_methods
    op.add_column('shipping_methods', sa.Column('carrier', sa.String(50), nullable=True))
    op.add_column('shipping_methods', sa.Column('auto_select_for_zones', postgresql.JSONB(), default=list))
    op.add_column('shipping_methods', sa.Column('max_weight_kg', sa.Float(), nullable=True))
    op.add_column('shipping_methods', sa.Column('max_items', sa.Integer(), nullable=True))
    
    # Create shipping_carriers table
    op.create_table(
        'shipping_carriers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('code', sa.String(20), unique=True, nullable=False),
        sa.Column('api_key', sa.String(255), nullable=True),
        sa.Column('api_secret', sa.String(255), nullable=True),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('auto_create_labels', sa.Boolean(), default=False),
        sa.Column('auto_schedule_pickup', sa.Boolean(), default=False),
        sa.Column('auto_track_shipments', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create shipping_automation_rules table
    op.create_table(
        'shipping_automation_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('conditions', postgresql.JSONB(), nullable=False),
        sa.Column('actions', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('shipping_automation_rules')
    op.drop_table('shipping_carriers')
    op.drop_column('shipping_methods', 'max_items')
    op.drop_column('shipping_methods', 'max_weight_kg')
    op.drop_column('shipping_methods', 'auto_select_for_zones')
    op.drop_column('shipping_methods', 'carrier')
    op.drop_column('delivery_zones', 'auto_assign')
    op.drop_column('delivery_zones', 'default_carrier')
