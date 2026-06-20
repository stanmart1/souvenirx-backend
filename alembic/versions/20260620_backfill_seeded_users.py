"""Backfill seeded/demo users as email_verified + created_by_admin

Revision ID: 20260620_backfill_seeded
Revises: 20260620_merge_heads
Create Date: 2026-06-20

The original seed script (``app/seed.py``) created the admin and demo
customer accounts without setting ``email_verified`` or
``created_by_admin``.  The ``20260618_add_user_created_by_admin``
migration only backfilled admin-role users, so the seeded demo customer
(``demo@souvenirx.com``) was left with ``email_verified=false`` and
``created_by_admin=false`` — causing the mobile app to send it through
the OTP flow even though it was a seed/admin-provisioned account.

This migration backfills the known seeded accounts so they skip OTP.
It is idempotent and safe to re-run.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260620_backfill_seeded'
down_revision = '20260620_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    users = sa.table(
        'users',
        sa.column('email', sa.String()),
        sa.column('email_verified', sa.Boolean()),
        sa.column('created_by_admin', sa.Boolean()),
    )
    # Backfill the known seeded accounts.
    op.execute(
        users.update()
        .where(users.c.email.in_(['admin@souvenirx.com', 'demo@souvenirx.com']))
        .values(email_verified=True, created_by_admin=True)
    )


def downgrade() -> None:
    # No-op — reverting would lock users out of their accounts.
    pass
