"""Add review moderation fields

Add is_approved, is_featured, admin_reply, admin_reply_at to reviews table
to support admin moderation workflow.

Revision ID: 20260617_add_review_moderation
Revises: 20260616_add_product_customizations
Create Date: 2026-06-17 00:00:00.000000
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260617_add_review_moderation'
down_revision: Union[str, None] = '20260616_add_product_customizations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add moderation columns to reviews table
    op.add_column('reviews', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('reviews', sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('reviews', sa.Column('admin_reply', sa.Text(), nullable=True))
    op.add_column('reviews', sa.Column('admin_reply_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('reviews', 'admin_reply_at')
    op.drop_column('reviews', 'admin_reply')
    op.drop_column('reviews', 'is_featured')
    op.drop_column('reviews', 'is_approved')
