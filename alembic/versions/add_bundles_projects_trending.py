"""Add product bundles, user projects, and trending templates

Revision ID: add_bundles_projects
Revises: 20260618_002
Create Date: 2026-06-16 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_bundles_projects'
down_revision = '20260618_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_bundles table
    op.create_table(
        'product_bundles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tagline', sa.String(length=500), nullable=True),
        sa.Column('original_price', sa.Integer(), nullable=False),
        sa.Column('discounted_price', sa.Integer(), nullable=False),
        sa.Column('discount_percentage', sa.Integer(), nullable=True),
        sa.Column('product_ids', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('bundle_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('banner_images', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('delivery_time', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('stock_status', sa.String(length=50), nullable=True),
        sa.Column('available_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('available_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('purchase_count', sa.Integer(), nullable=True),
        sa.Column('popularity_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_bundles_slug'), 'product_bundles', ['slug'], unique=True)
    op.create_index(op.f('ix_product_bundles_is_featured'), 'product_bundles', ['is_featured'], unique=False)
    op.create_index(op.f('ix_product_bundles_is_active'), 'product_bundles', ['is_active'], unique=False)

    # Create user_projects table
    op.create_table(
        'user_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('design_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('preview_url', sa.String(length=500), nullable=True),
        sa.Column('completion_percentage', sa.Integer(), nullable=True),
        sa.Column('current_step', sa.Integer(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('last_edited_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['design_id'], ['customer_designs.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['design_templates.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_projects_user_id'), 'user_projects', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_projects_status'), 'user_projects', ['status'], unique=False)

    # Create trending_templates table
    op.create_table(
        'trending_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('trending_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('view_count_24h', sa.Integer(), nullable=True),
        sa.Column('usage_count_7d', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=True),
        sa.Column('featured_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('featured_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['design_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trending_templates_template_id'), 'trending_templates', ['template_id'], unique=False)
    op.create_index(op.f('ix_trending_templates_display_order'), 'trending_templates', ['display_order'], unique=False)
    op.create_index(op.f('ix_trending_templates_is_active'), 'trending_templates', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trending_templates_is_active'), table_name='trending_templates')
    op.drop_index(op.f('ix_trending_templates_display_order'), table_name='trending_templates')
    op.drop_index(op.f('ix_trending_templates_template_id'), table_name='trending_templates')
    op.drop_table('trending_templates')
    
    op.drop_index(op.f('ix_user_projects_status'), table_name='user_projects')
    op.drop_index(op.f('ix_user_projects_user_id'), table_name='user_projects')
    op.drop_table('user_projects')
    
    op.drop_index(op.f('ix_product_bundles_is_active'), table_name='product_bundles')
    op.drop_index(op.f('ix_product_bundles_is_featured'), table_name='product_bundles')
    op.drop_index(op.f('ix_product_bundles_slug'), table_name='product_bundles')
    op.drop_table('product_bundles')
