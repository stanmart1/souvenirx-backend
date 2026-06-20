"""Drop legacy role and active_role columns from users

Revision ID: 20260620_drop_legacy_role
Revises: 20260620_add_rbac_tables
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260620_drop_legacy_role'
down_revision = '20260620_add_rbac_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('users', 'role')
    op.drop_column('users', 'active_role')


def downgrade() -> None:
    # Recreate the legacy columns and backfill from the RBAC tables.
    op.add_column('users', sa.Column('role', sa.String(100), nullable=False, server_default='customer'))
    op.add_column('users', sa.Column('active_role', sa.String(20), nullable=True))

    conn = op.get_bind()
    # Backfill role string from user_roles
    conn.execute(sa.text("""
        UPDATE users SET role = COALESCE((
            SELECT string_agg(r.name, ',' ORDER BY r.name)
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = users.id
        ), 'customer')
    """))
    # Backfill active_role string from active_role_id
    conn.execute(sa.text("""
        UPDATE users SET active_role = (
            SELECT r.name FROM roles r WHERE r.id = users.active_role_id
        )
    """))
    op.alter_column('users', 'role', server_default=None)
