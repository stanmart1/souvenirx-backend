"""Merge migration heads

Revision ID: 20260622_merge_heads
Revises: 20260620_backfill_seeded, 20260621_add_product_customization_options
Create Date: 2026-06-22

The migration graph diverged at ``20260620_merge_heads`` into two parallel branches:

  1. ``20260620_backfill_seeded`` - Backfill seeded/demo users
  2. ``20260621_add_product_customization_options`` - Add customization_options to products

Both branches are required in production, so this merge migration joins them
back into a single head. Without it ``alembic upgrade head`` fails with
"Multiple head revisions are present" and the backend container refuses to start.

This is a pure merge point — no schema changes.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260622_merge_heads'
down_revision = ('20260620_backfill_seeded', '20260621_add_product_customization_options')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration — no schema changes.
    pass


def downgrade() -> None:
    # Merge migration — no schema changes.
    pass
