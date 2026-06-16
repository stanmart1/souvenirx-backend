"""Merge migration heads

Revision ID: 20260617_merge_heads
Revises: 20260118_add_multi_role_support, 20260617_add_fcm_token
Create Date: 2026-06-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260617_merge_heads'
down_revision = ('20260118_add_multi_role_support', '20260617_add_fcm_token')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration - no changes needed
    pass


def downgrade() -> None:
    # This is a merge migration - no changes needed
    pass
