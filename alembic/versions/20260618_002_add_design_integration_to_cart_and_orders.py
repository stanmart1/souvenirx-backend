"""add design integration to cart and orders

Revision ID: 20260618_002
Revises: 20260618_add_design_template_system
Create Date: 2026-06-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260618_002'
down_revision = '20260618_add_design_template_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add customer_design_id to cart_items
    op.add_column('cart_items', sa.Column('customer_design_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_cart_items_customer_design_id',
        'cart_items',
        'customer_designs',
        ['customer_design_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add customer_design_id and design_preview_url to order_items
    op.add_column('order_items', sa.Column('customer_design_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('order_items', sa.Column('design_preview_url', sa.String(500), nullable=True))
    op.create_foreign_key(
        'fk_order_items_customer_design_id',
        'order_items',
        'customer_designs',
        ['customer_design_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove from order_items
    op.drop_constraint('fk_order_items_customer_design_id', 'order_items', type_='foreignkey')
    op.drop_column('order_items', 'design_preview_url')
    op.drop_column('order_items', 'customer_design_id')
    
    # Remove from cart_items
    op.drop_constraint('fk_cart_items_customer_design_id', 'cart_items', type_='foreignkey')
    op.drop_column('cart_items', 'customer_design_id')
