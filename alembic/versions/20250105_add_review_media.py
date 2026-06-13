"""Add media support to reviews

Revision ID: 20250105_add_review_media
Revises: 20250104_add_support_tickets
Create Date: 2025-01-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250105_add_review_media'
down_revision = '20250104_add_support_tickets'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reviews', sa.Column('media_url', sa.String(500), nullable=True))
    op.add_column('reviews', sa.Column('media_type', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('reviews', 'media_type')
    op.drop_column('reviews', 'media_url')
