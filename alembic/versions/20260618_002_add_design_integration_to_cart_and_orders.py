"""add design integration to cart and orders

Revision ID: 20260618_002
Revises: 20260618_add_design_template_system
Create Date: 2026-06-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20260618_002'
down_revision = '20260618_add_design_template_system'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    return column in [c['name'] for c in inspect(bind).get_columns(table)]


def _fk_exists(table, fk_name):
    bind = op.get_bind()
    return fk_name in [fk['name'] for fk in inspect(bind).get_foreign_keys(table)]


def upgrade() -> None:
    # Add customer_design_id to cart_items
    if not _column_exists('cart_items', 'customer_design_id'):
        op.add_column('cart_items', sa.Column('customer_design_id', postgresql.UUID(as_uuid=True), nullable=True))
    if not _fk_exists('cart_items', 'fk_cart_items_customer_design_id'):
        op.create_foreign_key(
            'fk_cart_items_customer_design_id',
            'cart_items',
            'customer_designs',
            ['customer_design_id'],
            ['id'],
            ondelete='SET NULL'
        )

    # Add customer_design_id and design_preview_url to order_items
    if not _column_exists('order_items', 'customer_design_id'):
        op.add_column('order_items', sa.Column('customer_design_id', postgresql.UUID(as_uuid=True), nullable=True))
    if not _column_exists('order_items', 'design_preview_url'):
        op.add_column('order_items', sa.Column('design_preview_url', sa.String(500), nullable=True))
    if not _fk_exists('order_items', 'fk_order_items_customer_design_id'):
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
    if _fk_exists('order_items', 'fk_order_items_customer_design_id'):
        op.drop_constraint('fk_order_items_customer_design_id', 'order_items', type_='foreignkey')
    if _column_exists('order_items', 'design_preview_url'):
        op.drop_column('order_items', 'design_preview_url')
    if _column_exists('order_items', 'customer_design_id'):
        op.drop_column('order_items', 'customer_design_id')

    # Remove from cart_items
    if _fk_exists('cart_items', 'fk_cart_items_customer_design_id'):
        op.drop_constraint('fk_cart_items_customer_design_id', 'cart_items', type_='foreignkey')
    if _column_exists('cart_items', 'customer_design_id'):
        op.drop_column('cart_items', 'customer_design_id')
