"""Add fcm_token column to users table

Revision ID: 20260617_add_fcm_token
Revises: 20250616_001
Create Date: 2024-06-17

"""
from alembic import op
import sqlalchemy as sa

revision = "20260617_add_fcm_token"
down_revision = "20250616_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("fcm_token", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "fcm_token")
