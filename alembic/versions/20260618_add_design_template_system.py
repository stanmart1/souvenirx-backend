"""Add design template and logo upload system

Revision ID: 20260618_add_design_template_system
Revises: 20260617_merge_heads
Create Date: 2026-06-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20260618_add_design_template_system'
down_revision = '20260617_merge_heads'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column already exists on a table."""
    bind = op.get_bind()
    return column in [c['name'] for c in inspect(bind).get_columns(table)]


def _index_exists(table, index):
    """Check if an index already exists on a table."""
    bind = op.get_bind()
    return index in [i['name'] for i in inspect(bind).get_indexes(table)]


def _table_exists(table):
    """Check if a table already exists."""
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def upgrade() -> None:
    # Create design_templates table
    if not _table_exists('design_templates'):
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
    if not _table_exists('customer_designs'):
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

    # Update logo_uploads table (add new columns to existing table idempotently)
    logo_cols = {
        'original_filename': sa.Column('original_filename', sa.String(255)),
        'file_size': sa.Column('file_size', sa.Integer()),
        'file_format': sa.Column('file_format', sa.String(10)),
        'mime_type': sa.Column('mime_type', sa.String(100)),
        'width': sa.Column('width', sa.Integer()),
        'height': sa.Column('height', sa.Integer()),
        'aspect_ratio': sa.Column('aspect_ratio', sa.Float()),
        'thumbnail_url': sa.Column('thumbnail_url', sa.String(500)),
        'optimized_url': sa.Column('optimized_url', sa.String(500)),
        'transparent_url': sa.Column('transparent_url', sa.String(500)),
        'has_transparency': sa.Column('has_transparency', sa.Boolean(), server_default='false'),
        'dominant_colors': sa.Column('dominant_colors', postgresql.JSONB()),
        'is_vector': sa.Column('is_vector', sa.Boolean(), server_default='false'),
        'processing_status': sa.Column('processing_status', sa.String(20), server_default='pending'),
        'processing_error': sa.Column('processing_error', sa.Text()),
        'usage_count': sa.Column('usage_count', sa.Integer(), server_default='0'),
        'last_used_at': sa.Column('last_used_at', sa.DateTime(timezone=True)),
        'name': sa.Column('name', sa.String(255)),
        'tags': sa.Column('tags', postgresql.JSONB()),
        'is_favorite': sa.Column('is_favorite', sa.Boolean(), server_default='false'),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    }
    for col_name, col_def in logo_cols.items():
        if not _column_exists('logo_uploads', col_name):
            op.add_column('logo_uploads', col_def)

    # Create indexes for logo_uploads
    logo_indexes = [
        ('idx_logo_upload_user_status', 'logo_uploads', ['user_id', 'status']),
        ('idx_logo_upload_created', 'logo_uploads', ['created_at']),
        ('idx_logo_upload_processing', 'logo_uploads', ['processing_status']),
    ]
    for idx_name, table, columns in logo_indexes:
        if not _index_exists(table, idx_name):
            op.create_index(idx_name, table, columns)

    # Create logo_overlay_configs table
    if not _table_exists('logo_overlay_configs'):
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
    if not _table_exists('product_mockup_templates'):
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
    if _table_exists('product_mockup_templates'):
        op.drop_table('product_mockup_templates')

    if _table_exists('logo_overlay_configs'):
        op.drop_table('logo_overlay_configs')

    # Remove added columns from logo_uploads (only if they exist)
    for col_name in [
        'updated_at', 'is_favorite', 'tags', 'name', 'last_used_at',
        'usage_count', 'processing_error', 'processing_status', 'is_vector',
        'dominant_colors', 'has_transparency', 'transparent_url',
        'optimized_url', 'thumbnail_url', 'aspect_ratio', 'height',
        'width', 'mime_type', 'file_format', 'file_size', 'original_filename'
    ]:
        if _column_exists('logo_uploads', col_name):
            op.drop_column('logo_uploads', col_name)

    if _table_exists('customer_designs'):
        op.drop_table('customer_designs')

    if _table_exists('design_templates'):
        op.drop_table('design_templates')
