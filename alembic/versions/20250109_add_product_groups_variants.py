"""Add product groups and variants support

Revision ID: 20250109_add_product_groups_variants
Revises: 20250108_add_payment_methods
Create Date: 2025-01-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250109_add_product_groups_variants'
down_revision = '20250108_add_payment_methods'
branch_labels = None
depends_on = None


def upgrade():
    # Create product_groups table
    op.create_table(
        'product_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Add columns to products table for grouped and variable products
    op.add_column('products', sa.Column('product_group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('products', sa.Column('is_group_parent', sa.Boolean(), default=False))
    op.add_column('products', sa.Column('has_variants', sa.Boolean(), default=False))
    
    # Create foreign key for product_group_id
    op.create_foreign_key('fk_products_product_group', 'products', 'product_groups', ['product_group_id'], ['id'])
    
    # Create product_variants table
    op.create_table(
        'product_variants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(100), unique=True, nullable=False),
        sa.Column('attributes', postgresql.JSONB(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('moq', sa.Integer(), nullable=False),
        sa.Column('stock', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_foreign_key('fk_variants_product', 'product_variants', 'products', ['product_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('fk_variants_product', 'product_variants', type_='foreignkey')
    op.drop_table('product_variants')
    op.drop_constraint('fk_products_product_group', 'products', type_='foreignkey')
    op.drop_column('products', 'has_variants')
    op.drop_column('products', 'is_group_parent')
    op.drop_column('products', 'product_group_id')
    op.drop_table('product_groups')
