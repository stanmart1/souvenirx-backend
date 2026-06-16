"""Add design template and logo upload system

Revision ID: 20260618_add_design_template_system
Revises: 20260617_merge_heads
Create Date: 2026-06-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260618_add_design_template_system'
down_revision = '20260617_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create design_templates table
    op.create_table(
        'design_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('style', sa.String(100), nullable=False),
        sa.Column('tags', postgresql.JSONB()),
        sa.Column('design_data', postgresql.JSONB(), nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=False),
        sa.Column('preview_images', postgresql.JSONB()),
        sa.Column('compatible_products', postgresql.JSONB()),
        sa.Column('is_premium', sa.Boolean(), default=False),
        sa.Column('premium_price', sa.Integer(), default=0),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('popularity_score', sa.Float(), default=0.0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_featured', sa.Boolean(), default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create indexes for design_templates
    op.create_index('idx_design_template_slug', 'design_templates', ['slug'])
    op.create_index('idx_design_template_category', 'design_templates', ['category'])
    op.create_index('idx_template_category_active', 'design_templates', ['category', 'is_active'])
    op.create_index('idx_template_popularity', 'design_templates', ['popularity_score'])
    op.create_index('idx_design_template_active', 'design_templates', ['is_active'])
    
    # Create customer_designs table
    op.create_table(
        'customer_designs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('design_templates.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('design_data', postgresql.JSONB(), nullable=False),
        sa.Column('preview_url', sa.String(500)),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('name', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create indexes for customer_designs
    op.create_index('idx_customer_design_user', 'customer_designs', ['user_id', 'status'])
    op.create_index('idx_customer_design_created', 'customer_designs', ['created_at'])
    op.create_index('idx_customer_design_status', 'customer_designs', ['status'])
    
    # Update logo_uploads table (add new columns to existing table)
    # Note: The table already exists from previous migrations, we're enhancing it
    op.add_column('logo_uploads', sa.Column('original_filename', sa.String(255)))
    op.add_column('logo_uploads', sa.Column('file_size', sa.Integer()))
    op.add_column('logo_uploads', sa.Column('file_format', sa.String(10)))
    op.add_column('logo_uploads', sa.Column('mime_type', sa.String(100)))
    op.add_column('logo_uploads', sa.Column('width', sa.Integer()))
    op.add_column('logo_uploads', sa.Column('height', sa.Integer()))
    op.add_column('logo_uploads', sa.Column('aspect_ratio', sa.Float()))
    op.add_column('logo_uploads', sa.Column('thumbnail_url', sa.String(500)))
    op.add_column('logo_uploads', sa.Column('optimized_url', sa.String(500)))
    op.add_column('logo_uploads', sa.Column('transparent_url', sa.String(500)))
    op.add_column('logo_uploads', sa.Column('has_transparency', sa.Boolean(), server_default='false'))
    op.add_column('logo_uploads', sa.Column('dominant_colors', postgresql.JSONB()))
    op.add_column('logo_uploads', sa.Column('is_vector', sa.Boolean(), server_default='false'))
    op.add_column('logo_uploads', sa.Column('processing_status', sa.String(20), server_default='pending'))
    op.add_column('logo_uploads', sa.Column('processing_error', sa.Text()))
    op.add_column('logo_uploads', sa.Column('usage_count', sa.Integer(), server_default='0'))
    op.add_column('logo_uploads', sa.Column('last_used_at', sa.DateTime(timezone=True)))
    op.add_column('logo_uploads', sa.Column('name', sa.String(255)))
    op.add_column('logo_uploads', sa.Column('tags', postgresql.JSONB()))
    op.add_column('logo_uploads', sa.Column('is_favorite', sa.Boolean(), server_default='false'))
    op.add_column('logo_uploads', sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()))
    
    # Create indexes for logo_uploads
    op.create_index('idx_logo_upload_user_status', 'logo_uploads', ['user_id', 'status'])
    op.create_index('idx_logo_upload_created', 'logo_uploads', ['created_at'])
    op.create_index('idx_logo_upload_processing', 'logo_uploads', ['processing_status'])
    
    # Create logo_overlay_configs table
    op.create_table(
        'logo_overlay_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_design_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customer_designs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('logo_upload_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('logo_uploads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position_x', sa.Float(), nullable=False, default=0.5),
        sa.Column('position_y', sa.Float(), nullable=False, default=0.5),
        sa.Column('scale', sa.Float(), nullable=False, default=0.2),
        sa.Column('rotation', sa.Float(), default=0.0),
        sa.Column('opacity', sa.Float(), default=1.0),
        sa.Column('flip_horizontal', sa.Boolean(), default=False),
        sa.Column('flip_vertical', sa.Boolean(), default=False),
        sa.Column('brightness', sa.Float(), default=1.0),
        sa.Column('contrast', sa.Float(), default=1.0),
        sa.Column('saturation', sa.Float(), default=1.0),
        sa.Column('color_overlay', sa.String(7)),
        sa.Column('color_overlay_opacity', sa.Float(), default=0.0),
        sa.Column('remove_background', sa.Boolean(), default=False),
        sa.Column('background_color', sa.String(7)),
        sa.Column('border_width', sa.Integer(), default=0),
        sa.Column('border_color', sa.String(7)),
        sa.Column('shadow_enabled', sa.Boolean(), default=False),
        sa.Column('shadow_blur', sa.Integer(), default=10),
        sa.Column('shadow_offset_x', sa.Integer(), default=5),
        sa.Column('shadow_offset_y', sa.Integer(), default=5),
        sa.Column('shadow_color', sa.String(9), default='#00000080'),
        sa.Column('z_index', sa.Integer(), default=0),
        sa.Column('lock_aspect_ratio', sa.Boolean(), default=True),
        sa.Column('min_scale', sa.Float(), default=0.05),
        sa.Column('max_scale', sa.Float(), default=0.8),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create indexes for logo_overlay_configs
    op.create_index('idx_logo_overlay_design', 'logo_overlay_configs', ['customer_design_id'])
    op.create_index('idx_logo_overlay_z_index', 'logo_overlay_configs', ['customer_design_id', 'z_index'])
    
    # Create product_mockup_templates table
    op.create_table(
        'product_mockup_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('mockup_image_url', sa.String(500), nullable=False),
        sa.Column('design_area', postgresql.JSONB(), nullable=False),
        sa.Column('view_type', sa.String(50), nullable=False),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for product_mockup_templates
    op.create_index('idx_mockup_product', 'product_mockup_templates', ['product_id', 'is_primary'])
    op.create_index('idx_mockup_sort', 'product_mockup_templates', ['product_id', 'sort_order'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('product_mockup_templates')
    op.drop_table('logo_overlay_configs')
    
    # Remove added columns from logo_uploads
    op.drop_column('logo_uploads', 'updated_at')
    op.drop_column('logo_uploads', 'is_favorite')
    op.drop_column('logo_uploads', 'tags')
    op.drop_column('logo_uploads', 'name')
    op.drop_column('logo_uploads', 'last_used_at')
    op.drop_column('logo_uploads', 'usage_count')
    op.drop_column('logo_uploads', 'processing_error')
    op.drop_column('logo_uploads', 'processing_status')
    op.drop_column('logo_uploads', 'is_vector')
    op.drop_column('logo_uploads', 'dominant_colors')
    op.drop_column('logo_uploads', 'has_transparency')
    op.drop_column('logo_uploads', 'transparent_url')
    op.drop_column('logo_uploads', 'optimized_url')
    op.drop_column('logo_uploads', 'thumbnail_url')
    op.drop_column('logo_uploads', 'aspect_ratio')
    op.drop_column('logo_uploads', 'height')
    op.drop_column('logo_uploads', 'width')
    op.drop_column('logo_uploads', 'mime_type')
    op.drop_column('logo_uploads', 'file_format')
    op.drop_column('logo_uploads', 'file_size')
    op.drop_column('logo_uploads', 'original_filename')
    
    op.drop_table('customer_designs')
    op.drop_table('design_templates')
