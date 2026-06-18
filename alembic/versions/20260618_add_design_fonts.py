"""Add design_fonts catalogue

Revision ID: 20260618_add_design_fonts
Revises: 20260620_loyalty_system
Create Date: 2026-06-18 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20260618_add_design_fonts'
down_revision = '20260620_loyalty_system'
branch_labels = None
depends_on = None


_SEED_FONTS = [
    # Script
    {"name": "Great Vibes", "display_name": "Great Vibes", "category": "script", "sort_order": 10,
     "preview_text": "Elegant celebrations"},
    {"name": "Allura", "display_name": "Allura", "category": "script", "sort_order": 11,
     "preview_text": "Beautifully yours"},
    {"name": "Pinyon Script", "display_name": "Pinyon Script", "category": "script", "sort_order": 12,
     "preview_text": "With love"},
    {"name": "Alex Brush", "display_name": "Alex Brush", "category": "script", "sort_order": 13,
     "preview_text": "Forever & always"},
    # Serif
    {"name": "Playfair Display", "display_name": "Playfair Display", "category": "serif", "sort_order": 20,
     "preview_text": "Timeless & Classic"},
    {"name": "Cormorant Garamond", "display_name": "Cormorant Garamond", "category": "serif", "sort_order": 21,
     "preview_text": "Heritage & Craft"},
    # Sans-serif
    {"name": "Montserrat", "display_name": "Montserrat", "category": "sans-serif", "sort_order": 30,
     "preview_text": "MODERN MINIMAL"},
    {"name": "Poppins", "display_name": "Poppins", "category": "sans-serif", "sort_order": 31,
     "preview_text": "Friendly & Fun"},
    {"name": "Lato", "display_name": "Lato", "category": "sans-serif", "sort_order": 32,
     "preview_text": "Everyday clarity"},
    # Handwritten
    {"name": "Dancing Script", "display_name": "Dancing Script", "category": "handwritten", "sort_order": 40,
     "preview_text": "Happy days!"},
    {"name": "Caveat", "display_name": "Caveat", "category": "handwritten", "sort_order": 41,
     "preview_text": "Notes from the heart"},
    {"name": "Pacifico", "display_name": "Pacifico", "category": "handwritten", "sort_order": 42,
     "preview_text": "Coastal vibes"},
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'design_fonts' in inspector.get_table_names():
        return

    op.create_table(
        'design_fonts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(150), nullable=False, unique=True),
        sa.Column('display_name', sa.String(150), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('preview_text', sa.String(120), nullable=False, server_default='AaBbCc 123'),
        sa.Column('sample_image_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_design_fonts_name', 'design_fonts', ['name'])
    op.create_index('ix_design_fonts_category', 'design_fonts', ['category'])
    op.create_index('ix_design_fonts_is_active', 'design_fonts', ['is_active'])
    op.create_index('idx_design_fonts_active_order', 'design_fonts', ['is_active', 'sort_order'])

    fonts_table = sa.table(
        'design_fonts',
        sa.column('name', sa.String()),
        sa.column('display_name', sa.String()),
        sa.column('category', sa.String()),
        sa.column('source_type', sa.String()),
        sa.column('preview_text', sa.String()),
        sa.column('is_active', sa.Boolean()),
        sa.column('is_premium', sa.Boolean()),
        sa.column('sort_order', sa.Integer()),
    )
    op.bulk_insert(
        fonts_table,
        [
            {
                'name': f['name'],
                'display_name': f['display_name'],
                'category': f['category'],
                'source_type': 'google',
                'preview_text': f['preview_text'],
                'is_active': True,
                'is_premium': False,
                'sort_order': f['sort_order'],
            }
            for f in _SEED_FONTS
        ],
    )


def downgrade() -> None:
    op.drop_index('idx_design_fonts_active_order', table_name='design_fonts')
    op.drop_index('ix_design_fonts_is_active', table_name='design_fonts')
    op.drop_index('ix_design_fonts_category', table_name='design_fonts')
    op.drop_index('ix_design_fonts_name', table_name='design_fonts')
    op.drop_table('design_fonts')
