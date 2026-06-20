"""Merge migration heads

Revision ID: 20260620_merge_heads
Revises: 20260618_add_user_created_by_admin, 20260620_drop_legacy_role
Create Date: 2026-06-20

The migration graph diverged at ``20260620_user_avatar_loyalty`` into two
parallel branches:

  1. ``20260620_loyalty_system`` -> ``20260618_add_design_fonts``
     -> ``20260618_add_user_created_by_admin``

  2. ``20260620_add_rbac_tables`` -> ``20260620_drop_legacy_role``

Both branches are required in production, so this merge migration joins them
back into a single head. Without it ``alembic upgrade head`` fails with
"Multiple head revisions are present" and the backend container refuses to
start (the 503 "no available server" seen from the mobile app).

This is a pure merge point — no schema changes.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260620_merge_heads'
down_revision = ('20260618_add_user_created_by_admin', '20260620_drop_legacy_role')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration — no schema changes.
    pass


def downgrade() -> None:
    # Merge migration — no schema changes.
    pass
