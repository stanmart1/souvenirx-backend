"""Add avatar_url and loyalty_points to users table

Revision ID: 20260620_user_avatar_loyalty
Revises: 20260620_category_image_desc
Create Date: 2026-06-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260620_user_avatar_loyalty'
down_revision = '20260620_category_image_desc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    existing = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users'"
            )
        )
    }

    if 'avatar_url' not in existing:
        op.add_column(
            'users',
            sa.Column('avatar_url', sa.String(500), nullable=True),
        )

    if 'loyalty_points' not in existing:
        op.add_column(
            'users',
            sa.Column('loyalty_points', sa.Integer(), server_default='0', nullable=False),
        )


def downgrade() -> None:
    op.drop_column('users', 'loyalty_points')
    op.drop_column('users', 'avatar_url')
