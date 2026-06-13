"""Add testimonials table

Revision ID: 20250106_add_testimonials_table
Revises: 20250105_add_review_media
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250106_add_testimonials_table'
down_revision = '20250105_add_review_media'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'testimonials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), default=5),
        sa.Column('media_url', sa.String(500), nullable=True),
        sa.Column('media_type', sa.String(20), nullable=True),
        sa.Column('is_approved', sa.Boolean(), default=False),
        sa.Column('is_featured', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('testimonials')
