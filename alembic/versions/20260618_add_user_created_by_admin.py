"""Add users.created_by_admin flag + mobile OTP columns

Revision ID: 20260618_add_user_created_by_admin
Revises: 20260618_add_design_fonts
Create Date: 2026-06-18 11:00:00.000000

Admins who create accounts from the dashboard should not need to go through
the OTP / email-verification flow — they already control the email address.

Also adds email_otp + email_otp_expires_at so self-signup users on the
mobile app can verify with a 6-digit code (in addition to the existing
URL-token flow used by the web app).
"""
from alembic import op
import sqlalchemy as sa


revision = '20260618_add_user_created_by_admin'
down_revision = '20260618_add_design_fonts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_cols = [c['name'] for c in inspector.get_columns('users')]

    # 1. created_by_admin flag
    if 'created_by_admin' not in existing_cols:
        op.add_column(
            'users',
            sa.Column(
                'created_by_admin',
                sa.Boolean(),
                nullable=False,
                server_default='false',
            ),
        )

    # 2. Mobile OTP columns
    if 'email_otp' not in existing_cols:
        op.add_column(
            'users',
            sa.Column('email_otp', sa.String(8), nullable=True),
        )
    if 'email_otp_expires_at' not in existing_cols:
        op.add_column(
            'users',
            sa.Column('email_otp_expires_at', sa.DateTime(timezone=True), nullable=True),
        )

    # 3. Mark all admin-role users as admin-created + email_verified
    #    (admin accounts are always provisioned by another admin / seed).
    users = sa.table(
        'users',
        sa.column('role', sa.String()),
        sa.column('email_verified', sa.Boolean()),
        sa.column('created_by_admin', sa.Boolean()),
    )
    op.execute(
        users.update()
        .where(users.c.role.ilike('%admin%'))
        .values(email_verified=True, created_by_admin=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'email_otp_expires_at')
    op.drop_column('users', 'email_otp')
    op.drop_column('users', 'created_by_admin')
