"""add multi-role support to users

Revision ID: 20260118_add_multi_role_support
Revises: 20260118_add_support_features
Create Date: 2026-01-18 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260118_add_multi_role_support'
down_revision = '20260118_add_support_features'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change role column to support comma-separated roles
    # Existing single roles will work as-is
    # New multi-role users will have "customer,affiliate" or "admin,customer" etc.
    op.alter_column('users', 'role',
                    existing_type=sa.String(20),
                    type_=sa.String(100),
                    existing_nullable=False)
    
    # Add a new column to track the active/current role for the session
    op.add_column('users', sa.Column('active_role', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'active_role')
    op.alter_column('users', 'role',
                    existing_type=sa.String(100),
                    type_=sa.String(20),
                    existing_nullable=False)
