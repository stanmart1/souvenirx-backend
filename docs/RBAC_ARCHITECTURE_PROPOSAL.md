# RBAC Architecture Proposal

## Status

Proposed — ready for review before implementation.

## Context

The SouvenirX application currently uses a simple comma-separated `role` column on the `users` table. The three supported roles are `customer`, `affiliate`, and `admin`. Access control is role-based: middleware checks `user.has_role("admin")` and the frontend branches on `isAdmin`, `isAffiliate`, and `isCustomer`.

This model is sufficient today, but it has limits:

- **Coarse access control.** Anyone with the `admin` role has the same access as every other admin. There is no way to grant a user read-only access, order-management-only access, or customer-support-only access.
- **Role strings are fragile.** Roles are stored as `customer,affiliate,admin` and parsed with `split(",")`. Filtering requires exact-match SQL gymnastics and is easy to break.
- **Role and entity drift.** The `affiliate` role requires a matching `affiliates` row. The current implementation now keeps these in sync, but the root cause is that a role and its backing entity are conflated.
- **Hard to audit.** There is no permissions table, so it is impossible to answer “who can delete orders?” without reading source code.

## Goal

Introduce a relational Role-Based Access Control (RBAC) system that:

1. Replaces the comma-separated role string with normalized `roles` and `permissions` tables.
2. Supports fine-grained permissions (e.g., `users:write`, `orders:read`).
3. Allows admins to create custom roles with a configurable permission set.
4. Provides a clean, reversible migration path from the current model.
5. Keeps the existing public API stable during the transition.

## Proposed data model

```text
users
  id (PK)
  email
  full_name
  phone
  is_active
  email_verified
  active_role_id (FK -> roles, nullable)
  password_hash
  created_at
  updated_at

roles
  id (PK)
  name (unique, slug, e.g. "admin", "customer", "affiliate", "support")
  label (human-readable, e.g. "Administrator")
  description
  is_system (bool, protects built-in roles from deletion)
  is_active (bool)
  created_at
  updated_at

permissions
  id (PK)
  resource (e.g. "users", "orders", "affiliates")
  action (e.g. "read", "write", "delete", "payout")
  description
  unique(resource, action)

role_permissions
  role_id (FK -> roles)
  permission_id (FK -> permissions)
  PK(role_id, permission_id)

user_roles
  user_id (FK -> users)
  role_id (FK -> roles)
  assigned_by (FK -> users, admin who assigned the role)
  assigned_at
  PK(user_id, role_id)

# Keep Affiliate as a business entity, not a role.
affiliates
  id (PK)
  user_id (FK -> users, unique)
  referral_code
  status
  commission_rate
  ...
```

## Role vs. permission semantics

- A **role** is a named collection of permissions. Roles are what users are assigned to.
- A **permission** is a single access grant on a resource/action pair. Permissions are what code checks.
- A user can have many roles. Their effective permissions are the union of all roles.
- `active_role_id` is optional and controls which dashboard the user lands on after login.

## Built-in roles (system roles)

| Role | Permissions |
|---|---|
| `customer` | `profile:read`, `profile:write`, `orders:read`, `orders:write`, `cart:read`, `cart:write`, `addresses:read`, `addresses:write`, `payment_methods:read`, `payment_methods:write` |
| `affiliate` | Everything in `customer`, plus `affiliate:read`, `affiliate:write`, `referrals:read`, `payouts:request` |
| `admin` | Full permissions (`*:*` or an explicit list of every permission) |
| `support` | `users:read`, `orders:read`, `orders:write`, `tickets:read`, `tickets:write` |
| `fulfillment` | `orders:read`, `orders:write`, `delivery:read`, `delivery:write` |

System roles (`is_system = true`) cannot be deleted, but admins can clone them to create custom roles.

## Permission catalog (v1)

```text
# User & role management
users:read           # View user list/profile
users:write          # Edit user details
users:delete         # Deactivate/delete users
roles:read           # View roles
roles:write          # Create/edit roles
roles:assign         # Assign/remove roles from users

# Catalog
products:read
products:write
products:delete
categories:read
categories:write

# Orders
orders:read
orders:write
orders:delete
orders:refund

# Payments & payouts
payment_methods:read
payment_methods:write
payouts:read
payouts:process
payouts:request

# Affiliates
affiliates:read
affiliates:write
affiliates:approve
referrals:read

# Marketing
promos:read
promos:write
campaigns:read
campaigns:write

# Content & config
homepage:write
settings:write
email_templates:write

# Customer support
reviews:read
reviews:write
tickets:read
tickets:write

# Customer self-service
profile:read
profile:write
cart:read
cart:write
addresses:read
addresses:write
```

## API and middleware changes

### New dependencies

```python
from functools import wraps
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def require_permission(permission: str):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if not await user.has_permission(permission):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return checker

# Usage
@router.post("/products", dependencies=[Depends(require_permission("products:write"))])
async def create_product(...):
    ...
```

### User model helper

```python
class User(Base):
    ...
    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", lazy="selectin")

    async def has_permission(self, permission: str, db: AsyncSession) -> bool:
        # Check wildcard admin
        if self.is_superuser:
            return True
        resource, action = permission.split(":", 1)
        result = await db.execute(
            select(func.count())
            .select_from(role_permissions)
            .join(Permission, role_permissions.c.permission_id == Permission.id)
            .join(user_roles, role_permissions.c.role_id == user_roles.c.role_id)
            .where(
                user_roles.c.user_id == self.id,
                Permission.resource.in_([resource, "*"]),
                Permission.action.in_([action, "*"]),
            )
        )
        return result.scalar() > 0
```

### Backward-compatible role helpers

```python
async def is_admin(user: User, db: AsyncSession) -> bool:
    return await user.has_role("admin", db)

async def is_affiliate(user: User, db: AsyncSession) -> bool:
    return await user.has_role("affiliate", db)

async def is_customer(user: User, db: AsyncSession) -> bool:
    return await user.has_role("customer", db)
```

## Frontend changes

1. **Auth context** exposes `permissions: string[]` and helpers `hasPermission("orders:read")`.
2. **Sidebar** and **page guards** switch from `isAdmin` to `hasPermission` checks.
3. **Admin role management** page becomes a full CRUD for roles and permissions.
4. **User detail** page shows effective permissions and role history.

## Migration plan

The migration is split into four milestones so the app can be deployed incrementally.

### Milestone 1: Add tables and backfill (non-breaking)

1. Create Alembic migrations for `roles`, `permissions`, `role_permissions`, and `user_roles`.
2. Insert built-in roles and permissions.
3. Backfill `user_roles` from `User.role`:

```sql
INSERT INTO user_roles (user_id, role_id, assigned_at)
SELECT u.id, r.id, NOW()
FROM users u
JOIN roles r ON (
  (u.role = 'customer' AND r.name = 'customer') OR
  (u.role LIKE '%,customer' AND r.name = 'customer') OR
  (u.role LIKE 'customer,%' AND r.name = 'customer') OR
  (u.role LIKE '%,customer,%' AND r.name = 'customer')
)
-- Repeat for affiliate and admin
```

4. Backfill `active_role_id` from `User.active_role`.
5. Keep `User.role` column in place for rollback safety.

### Milestone 2: Dual-read (non-breaking)

1. Update `get_current_admin` and `get_current_user` helpers to check both `User.role` and the new tables.
2. Update `isAdmin`, `isAffiliate`, `isCustomer` in the auth context to query both sources.
3. Add a feature flag or kill switch to prefer the new tables.

### Milestone 3: Migrate endpoints to permissions

1. Replace `get_current_admin` with `require_permission(...)` on admin endpoints.
2. Update admin user-management UI to assign roles and show permissions.
3. Add new admin endpoints:
   - `GET /api/admin/roles`
   - `POST /api/admin/roles`
   - `PATCH /api/admin/roles/{id}`
   - `DELETE /api/admin/roles/{id}` (only if `is_system = false`)
   - `GET /api/admin/permissions`
   - `POST /api/admin/users/{id}/roles`
   - `DELETE /api/admin/users/{id}/roles/{role_id}`

### Milestone 4: Remove legacy role string

1. Remove `User.role` column.
2. Remove `User.active_role` column (already replaced by `active_role_id`).
3. Remove all `has_role` substring parsing.
4. Update the role filter in the user list to use `user_roles.role_id`.

## Rollback strategy

- Before Milestone 4, the `User.role` column remains populated by a database trigger or a periodic sync job.
- If a rollback is needed, disable the feature flag and revert to reading `User.role`.
- After Milestone 4, rollback requires a data migration script that reconstructs `User.role` from `user_roles`.

## Security considerations

- The `admin` role should be a system role with `*:*` wildcard permission.
- Never allow the `admin` role to be deleted or to have all permissions removed.
- Role assignment should be logged in the audit log (already implemented).
- The `roles:assign` permission must itself be tightly controlled.
- API endpoints should return 403, not 404, for permission failures to avoid leaking resource existence.

## Open questions

1. Should we support role hierarchies (e.g., `admin` inherits from `support`)?
2. Should permissions be scoped to specific stores/tenants if multi-tenancy is added later?
3. Should the frontend fetch the full permission list once at login, or per-route?

## Files added as part of this proposal

- `app/models/rbac.py` — `Role`, `Permission`, `user_roles`, and `role_permissions` models.
- `app/middleware/permissions.py` — `require_permission` dependency, `user_has_permission`, and `user_has_role` helpers.
- `app/models/user.py` — added `active_role_id` foreign key for the new roles table.
- `alembic/versions/20260620_add_rbac_tables.py` — migration that creates RBAC tables, seeds system roles/permissions, and backfills data from the legacy `role` and `active_role` columns.

## Recommended next steps

1. Review and approve this proposal.
2. Run the migration in a local/staging environment:
   ```bash
   source .venv/bin/activate
   alembic upgrade 20260620_add_rbac_tables
   ```
3. Wire `require_permission` into admin endpoints alongside the existing `get_current_admin` checks.
4. Update the admin user-management UI to read from the new endpoints.
5. Run a dry-run migration on a copy of production data to validate the backfill SQL.
