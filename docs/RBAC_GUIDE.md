# RBAC Guide — Roles & Permissions Management

This document describes the SouvenirX RBAC system, including the data model,
service functions, API endpoints, and admin UI workflows.

## Overview

SouvenirX uses a relational Role-Based Access Control (RBAC) system:

- **Users** are assigned one or more **Roles**.
- **Roles** are granted one or more **Permissions**.
- **Permissions** are `resource:action` pairs (e.g., `users:read`, `orders:write`).
- Wildcards are supported: `*:*` (all), `users:*` (all actions on users), `*:read` (read on everything).

The system supports fine-grained access control: instead of a single "admin"
role with blanket access, you can create custom roles with specific permission
sets (e.g., a "Support" role that can view orders and users but not edit products).

## Data Model

```
users ──< user_roles >── roles ──< role_permissions >── permissions
```

| Table | Description |
|-------|-------------|
| `users` | Application users. Has `active_role_id` for the currently active role. |
| `roles` | Role definitions (name, label, description, is_system, is_active). |
| `permissions` | Permission definitions (resource, action, description). |
| `user_roles` | Many-to-many: user ↔ role assignments. Tracks `assigned_by`. |
| `role_permissions` | Many-to-many: role ↔ permission grants. |

### System Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `admin` | Full access | `*:*` (wildcard) |
| `customer` | Shopper | orders, cart, addresses, profile (read/write) |
| `affiliate` | Referral partner | customer perms + referrals:read, payouts:request |
| `support` | Customer support | orders:read/write, tickets:read/write, users:read |
| `fulfillment` | Order fulfillment | orders:read/write |

System roles (`is_system = true`) cannot be deleted or deactivated.

## Backend Service API

All service functions are in `app/services/rbac.py`.

### Role CRUD

```python
from app.services.rbac import (
    create_role, update_role, delete_role, list_roles,
    get_role_by_id, get_role_by_name, get_role_with_permissions,
    list_roles_with_stats, count_users_with_role,
)

# Create a custom role
role = await create_role(db, name="editor", label="Editor", description="Content editor")

# Update a role
await update_role(db, role.id, label="Senior Editor", is_active=True)

# Delete a custom role (raises if system role or has users)
await delete_role(db, role.id)

# List all roles
roles = await list_roles(db, include_inactive=False)

# Get role with permissions and user count
detail = await get_role_with_permissions(db, role.id)
# Returns: {id, name, label, description, is_system, is_active, permissions, user_count}
```

### Permission CRUD

```python
from app.services.rbac import (
    create_permission, delete_permission, list_permissions,
    get_permission_by_id, get_permission_by_resource_action,
)

# Create a custom permission
perm = await create_permission(db, resource="blog", action="write", description="Write blog posts")

# Delete a permission (wildcard *:* cannot be deleted)
await delete_permission(db, perm.id)

# List all permissions
perms = await list_permissions(db)
```

### Role-Permission Management

```python
from app.services.rbac import (
    grant_permission, revoke_permission, set_role_permissions,
    get_role_permission_ids,
)

# Grant a permission to a role
await grant_permission(db, role_id, permission_id)

# Revoke a permission
await revoke_permission(db, role_id, permission_id)

# Replace all permissions for a role
await set_role_permissions(db, role_id, [perm_id_1, perm_id_2])
```

### User-Role Management

```python
from app.services.rbac import (
    assign_roles, add_role, remove_role, set_active_role,
    get_user_role_names, get_active_role_name, user_has_role,
)

# Replace user's role set
roles = await assign_roles(db, user, ["customer", "affiliate"], assigned_by=admin)

# Add a single role
roles = await add_role(db, user, "editor", assigned_by=admin)

# Remove a single role (raises if last role)
roles = await remove_role(db, user, "editor")

# Set active role
await set_active_role(db, user, "affiliate")
```

### Permission Checking

```python
from app.middleware.permissions import require_permission, user_has_permission

# As a FastAPI dependency
@router.post("/products", dependencies=[Depends(require_permission("products:write"))])
async def create_product(...):
    ...

# Direct check
if await user_has_permission(user, "orders:read", db):
    ...
```

## REST API Endpoints

All endpoints are under `/api/admin/rbac` and require `roles:read` or `roles:write`
permissions.

### Roles

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/roles` | `roles:read` | List all roles with permissions and user counts |
| POST | `/roles` | `roles:write` | Create a new custom role |
| GET | `/roles/{id}` | `roles:read` | Get a single role with permissions |
| PATCH | `/roles/{id}` | `roles:write` | Update role label/description/active status |
| DELETE | `/roles/{id}` | `roles:write` | Delete a custom role (not system roles) |

### Role Permissions

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/roles/{id}/permissions` | `roles:read` | List permissions for a role |
| PUT | `/roles/{id}/permissions` | `roles:write` | Replace all permissions for a role |
| POST | `/roles/{id}/permissions` | `roles:write` | Grant a single permission |
| DELETE | `/roles/{id}/permissions/{perm_id}` | `roles:write` | Revoke a single permission |

### Permissions

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/permissions` | `roles:read` | List all permissions |
| POST | `/permissions` | `roles:write` | Create a custom permission |
| DELETE | `/permissions/{id}` | `roles:write` | Delete a permission (not `*:*`) |

### User Roles

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/users/{id}/roles` | `roles:read` | List roles for a user |
| PUT | `/users/{id}/roles` | `roles:assign` | Replace all roles for a user |
| POST | `/users/{id}/roles` | `roles:assign` | Add a single role to a user |
| DELETE | `/users/{id}/roles/{role_name}` | `roles:assign` | Remove a single role from a user |

### Current User Permissions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/auth/me/permissions` | Any user | Get current user's roles, active role, and effective permissions |

## Audit Logging

All RBAC mutations are audit-logged via `app.services.audit.log_audit()`:

- `create_role`, `update_role`, `delete_role`
- `create_permission`, `delete_permission`
- `grant_permission`, `revoke_permission`, `replace_role_permissions`
- `replace_user_roles`, `add_user_role`, `remove_user_role`

Audit logs are viewable at `/api/admin/audit-logs` and in the admin UI at
`/admin/audit-logs`.

## Admin UI

### Roles & Permissions Page (`/admin/roles`)

- **Master-detail layout**: role list on the left, permission editor on the right.
- **Create custom roles**: click "New Role" to open the RoleEditor modal.
- **Edit permissions**: select a role, then toggle permissions in the PermissionMatrix.
  Click "Save" to persist changes.
- **Delete roles**: click the trash icon. System roles and roles with assigned
  users cannot be deleted.
- **Permission grouping**: permissions are grouped by resource with select-all-per-resource.

### User Management (`/admin/users`)

- The role assignment modal fetches available roles dynamically from the RBAC API.
- Custom roles created in the Roles & Permissions page are available for assignment.

### Frontend Permission Checks

```tsx
import { useAuth } from "@/lib/auth";
import { Can } from "@/components/admin/Can";
import { useCan } from "@/lib/useCan";

// Hook-based
function DeleteButton() {
  const can = useCan();
  if (!can("users:delete")) return null;
  return <button>Delete</button>;
}

// Component-based
<Can permission="users:delete" fallback={<span>Not allowed</span>}>
  <DeleteButton />
</Can>
```

## Permission Catalog

| Resource | Actions | Description |
|----------|---------|-------------|
| `*` | `*` | Wildcard — grants all permissions |
| `users` | `read`, `write` | User management |
| `roles` | `read`, `write`, `assign` | Role & permission management |
| `orders` | `read`, `write`, `delete`, `refund` | Order management |
| `products` | `read`, `write` | Product catalog |
| `cart` | `read`, `write` | Shopping cart |
| `addresses` | `read`, `write` | Shipping addresses |
| `profile` | `read`, `write` | User profile |
| `referrals` | `read` | Affiliate referrals |
| `payouts` | `request` | Affiliate payout requests |
| `tickets` | `read`, `write` | Support tickets |

Custom permissions can be created via the API or admin UI.
