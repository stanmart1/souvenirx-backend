"""Add RBAC roles and permissions tables

Revision ID: 20260620_add_rbac_tables
Revises: 20260620_user_avatar_loyalty
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260620_add_rbac_tables'
down_revision = '20260620_user_avatar_loyalty'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # roles
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # permissions
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )

    # role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # user_roles
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
    )

    # active_role_id FK on users
    op.add_column('users', sa.Column('active_role_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_users_active_role_id', 'users', 'roles', ['active_role_id'], ['id'])

    # Seed system roles and permissions
    if conn.dialect.name == 'postgresql':
        conn.execute(sa.text("""
            INSERT INTO roles (id, name, label, description, is_system, is_active)
            VALUES
                (gen_random_uuid(), 'customer', 'Customer', 'Default shopper role', true, true),
                (gen_random_uuid(), 'affiliate', 'Affiliate', 'Earns commission via referrals', true, true),
                (gen_random_uuid(), 'admin', 'Administrator', 'Full system access', true, true),
                (gen_random_uuid(), 'support', 'Support', 'Customer support access', true, true),
                (gen_random_uuid(), 'fulfillment', 'Fulfillment', 'Order and delivery management', true, true)
            ON CONFLICT (name) DO NOTHING;
        """))

        conn.execute(sa.text("""
            INSERT INTO permissions (id, resource, action, description)
            VALUES
                (gen_random_uuid(), '*', '*', 'Wildcard super-admin permission'),
                (gen_random_uuid(), 'users', 'read', 'View users'),
                (gen_random_uuid(), 'users', 'write', 'Edit users'),
                (gen_random_uuid(), 'users', 'delete', 'Deactivate/delete users'),
                (gen_random_uuid(), 'roles', 'read', 'View roles'),
                (gen_random_uuid(), 'roles', 'write', 'Create/edit roles'),
                (gen_random_uuid(), 'roles', 'assign', 'Assign roles to users'),
                (gen_random_uuid(), 'products', 'read', 'View products'),
                (gen_random_uuid(), 'products', 'write', 'Create/edit products'),
                (gen_random_uuid(), 'products', 'delete', 'Delete products'),
                (gen_random_uuid(), 'categories', 'read', 'View categories'),
                (gen_random_uuid(), 'categories', 'write', 'Create/edit categories'),
                (gen_random_uuid(), 'orders', 'read', 'View orders'),
                (gen_random_uuid(), 'orders', 'write', 'Update order status'),
                (gen_random_uuid(), 'orders', 'delete', 'Delete orders'),
                (gen_random_uuid(), 'orders', 'refund', 'Process refunds'),
                (gen_random_uuid(), 'payment_methods', 'read', 'View payment methods'),
                (gen_random_uuid(), 'payment_methods', 'write', 'Manage payment methods'),
                (gen_random_uuid(), 'payouts', 'read', 'View payouts'),
                (gen_random_uuid(), 'payouts', 'process', 'Process affiliate payouts'),
                (gen_random_uuid(), 'payouts', 'request', 'Request a payout'),
                (gen_random_uuid(), 'affiliates', 'read', 'View affiliates'),
                (gen_random_uuid(), 'affiliates', 'write', 'Edit affiliates'),
                (gen_random_uuid(), 'affiliates', 'approve', 'Approve affiliate applications'),
                (gen_random_uuid(), 'referrals', 'read', 'View referral history'),
                (gen_random_uuid(), 'promos', 'read', 'View promo codes'),
                (gen_random_uuid(), 'promos', 'write', 'Manage promo codes'),
                (gen_random_uuid(), 'campaigns', 'read', 'View campaigns'),
                (gen_random_uuid(), 'campaigns', 'write', 'Manage campaigns'),
                (gen_random_uuid(), 'homepage', 'write', 'Edit homepage content'),
                (gen_random_uuid(), 'settings', 'write', 'Edit system settings'),
                (gen_random_uuid(), 'email_templates', 'write', 'Edit email templates'),
                (gen_random_uuid(), 'reviews', 'read', 'View reviews'),
                (gen_random_uuid(), 'reviews', 'write', 'Moderate reviews'),
                (gen_random_uuid(), 'tickets', 'read', 'View support tickets'),
                (gen_random_uuid(), 'tickets', 'write', 'Manage support tickets'),
                (gen_random_uuid(), 'profile', 'read', 'View own profile'),
                (gen_random_uuid(), 'profile', 'write', 'Edit own profile'),
                (gen_random_uuid(), 'cart', 'read', 'View own cart'),
                (gen_random_uuid(), 'cart', 'write', 'Edit own cart'),
                (gen_random_uuid(), 'addresses', 'read', 'View own addresses'),
                (gen_random_uuid(), 'addresses', 'write', 'Edit own addresses')
            ON CONFLICT (resource, action) DO NOTHING;
        """))

        # Grant permissions to system roles.
        # admin: wildcard
        conn.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'admin' AND p.resource = '*' AND p.action = '*'
            ON CONFLICT DO NOTHING;
        """))

        # customer: profile, cart, addresses, orders read/write
        conn.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'customer'
              AND p.resource IN ('profile', 'cart', 'addresses', 'orders')
            ON CONFLICT DO NOTHING;
        """))

        # affiliate: everything customer has + affiliate/read, referrals/read, payouts/request
        conn.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'affiliate'
              AND (
                p.resource IN ('profile', 'cart', 'addresses', 'orders')
                OR (p.resource = 'affiliate' AND p.action = 'read')
                OR (p.resource = 'referrals' AND p.action = 'read')
                OR (p.resource = 'payouts' AND p.action = 'request')
              )
            ON CONFLICT DO NOTHING;
        """))

        # support: users/read, orders/read+write, tickets/read+write
        conn.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'support'
              AND (
                (p.resource = 'users' AND p.action = 'read')
                OR (p.resource = 'orders' AND p.action IN ('read', 'write'))
                OR (p.resource = 'tickets' AND p.action IN ('read', 'write'))
              )
            ON CONFLICT DO NOTHING;
        """))

        # fulfillment: orders/read+write, delivery (mapped to orders for now)
        conn.execute(sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'fulfillment'
              AND (
                (p.resource = 'orders' AND p.action IN ('read', 'write'))
              )
            ON CONFLICT DO NOTHING;
        """))

        # Backfill user_roles from the legacy comma-separated role string.
        conn.execute(sa.text("""
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            SELECT u.id, r.id, NOW()
            FROM users u
            CROSS JOIN roles r
            WHERE (
                u.role = r.name
                OR u.role LIKE r.name || ',%'
                OR u.role LIKE '%,' || r.name || ',%'
                OR u.role LIKE '%,' || r.name
            )
            ON CONFLICT (user_id, role_id) DO NOTHING;
        """))

        # Backfill active_role_id from legacy active_role string.
        conn.execute(sa.text("""
            UPDATE users u
            SET active_role_id = r.id
            FROM roles r
            WHERE u.active_role = r.name;
        """))


def downgrade() -> None:
    op.drop_constraint('fk_users_active_role_id', 'users', type_='foreignkey')
    op.drop_column('users', 'active_role_id')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
