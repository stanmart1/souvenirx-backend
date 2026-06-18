"""Add image and description fields to categories

Revision ID: 20260620_category_image_desc
Revises: 20260619_logo_moderation
Create Date: 2026-06-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260620_category_image_desc'
down_revision = '20260619_logo_moderation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    existing = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='categories'"
            )
        )
    }

    if 'image' not in existing:
        op.add_column(
            'categories',
            sa.Column('image', sa.String(500), nullable=True),
        )

    if 'description' not in existing:
        op.add_column(
            'categories',
            sa.Column('description', sa.String(255), nullable=True),
        )


def downgrade() -> None:
    op.drop_column('categories', 'description')
    op.drop_column('categories', 'image')
