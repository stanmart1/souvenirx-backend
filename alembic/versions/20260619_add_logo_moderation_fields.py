"""Add moderation fields to logo_uploads

Revision ID: 20260619_logo_moderation
Revises: add_bundles_projects
Create Date: 2026-06-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260619_logo_moderation'
down_revision = 'add_bundles_projects'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add moderation fields to logo_uploads — idempotent
    conn = op.get_bind()

    existing = {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='logo_uploads'"
            )
        )
    }

    if 'reviewed_by' not in existing:
        op.add_column(
            'logo_uploads',
            sa.Column(
                'reviewed_by',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('users.id', ondelete='SET NULL'),
                nullable=True,
            ),
        )

    if 'reviewed_at' not in existing:
        op.add_column(
            'logo_uploads',
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        )

    if 'rejection_reason' not in existing:
        op.add_column(
            'logo_uploads',
            sa.Column('rejection_reason', sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column('logo_uploads', 'rejection_reason')
    op.drop_column('logo_uploads', 'reviewed_at')
    op.drop_column('logo_uploads', 'reviewed_by')
