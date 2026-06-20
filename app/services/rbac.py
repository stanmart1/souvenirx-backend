"""RBAC role-management service.

This module is the single source of truth for managing roles, permissions,
and their assignments. All role/permission mutations should go through
these helpers so that the ``user_roles`` and ``role_permissions`` tables
stay consistent and audit log entries are written.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as sa_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, Role, role_permissions, user_roles
from app.models.user import User


# ---------------------------------------------------------------------------
# Role queries
# ---------------------------------------------------------------------------

async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    """Fetch a role by its unique slug."""
    result = await db.execute(select(Role).where(Role.name == name, Role.is_active.is_(True)))
    return result.scalar_one_or_none()


async def get_role_by_id(db: AsyncSession, role_id: UUID) -> Optional[Role]:
    """Fetch a role by its primary key."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def list_roles(db: AsyncSession, include_inactive: bool = False) -> list[Role]:
    """Return all roles, ordered by name. Excludes inactive roles by default."""
    query = select(Role).order_by(Role.name)
    if not include_inactive:
        query = query.where(Role.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_role_with_permissions(db: AsyncSession, role_id: UUID) -> Optional[dict]:
    """Return a role with its permissions and user count as a dict."""
    role = await get_role_by_id(db, role_id)
    if not role:
        return None
    perms_result = await db.execute(
        select(Permission)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .where(role_permissions.c.role_id == role.id)
        .order_by(Permission.resource, Permission.action)
    )
    permissions = list(perms_result.scalars().all())
    user_count_result = await db.execute(
        select(func.count())
        .select_from(user_roles)
        .where(user_roles.c.role_id == role.id)
    )
    user_count = user_count_result.scalar() or 0
    return {
        "id": str(role.id),
        "name": role.name,
        "label": role.label,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
        "user_count": user_count,
        "permissions": [
            {
                "id": str(p.id),
                "resource": p.resource,
                "action": p.action,
                "description": p.description,
            }
            for p in permissions
        ],
    }


async def count_users_with_role(db: AsyncSession, role_id: UUID) -> int:
    """Return the number of users assigned to a role."""
    result = await db.execute(
        select(func.count())
        .select_from(user_roles)
        .where(user_roles.c.role_id == role_id)
    )
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Role CRUD
# ---------------------------------------------------------------------------

async def create_role(
    db: AsyncSession,
    name: str,
    label: str,
    description: Optional[str] = None,
    is_system: bool = False,
) -> Role:
    """Create a new custom role. Raises ``ValueError`` if the name is taken."""
    existing = await get_role_by_name(db, name)
    # Also check inactive roles with the same name
    if not existing:
        result = await db.execute(select(Role).where(Role.name == name))
        existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Role '{name}' already exists")
    role = Role(
        name=name,
        label=label,
        description=description,
        is_system=is_system,
        is_active=True,
    )
    db.add(role)
    await db.flush()
    return role


async def update_role(
    db: AsyncSession,
    role_id: UUID,
    label: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Role:
    """Update a role's mutable fields. System roles cannot be deactivated."""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("Role not found")
    if role.is_system and is_active is False:
        raise ValueError("System roles cannot be deactivated")
    if label is not None:
        role.label = label
    if description is not None:
        role.description = description
    if is_active is not None:
        role.is_active = is_active
    await db.flush()
    return role


async def delete_role(db: AsyncSession, role_id: UUID) -> None:
    """Delete a custom role. System roles cannot be deleted.

    Raises ``ValueError`` if the role is a system role or has users assigned.
    """
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("Role not found")
    if role.is_system:
        raise ValueError("System roles cannot be deleted")
    user_count = await count_users_with_role(db, role_id)
    if user_count > 0:
        raise ValueError(
            f"Cannot delete role '{role.name}' — {user_count} user(s) are still assigned. "
            "Remove the role from all users first."
        )
    # role_permissions and user_roles rows cascade on delete
    await db.delete(role)
    await db.flush()


# ---------------------------------------------------------------------------
# Permission queries
# ---------------------------------------------------------------------------

async def list_permissions(db: AsyncSession) -> list[Permission]:
    """Return all permissions ordered by resource then action."""
    result = await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action)
    )
    return list(result.scalars().all())


async def get_permission_by_resource_action(
    db: AsyncSession, resource: str, action: str
) -> Optional[Permission]:
    """Fetch a permission by its resource:action pair."""
    result = await db.execute(
        select(Permission).where(
            Permission.resource == resource,
            Permission.action == action,
        )
    )
    return result.scalar_one_or_none()


async def get_permission_by_id(db: AsyncSession, permission_id: UUID) -> Optional[Permission]:
    """Fetch a permission by its primary key."""
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Permission CRUD
# ---------------------------------------------------------------------------

async def create_permission(
    db: AsyncSession,
    resource: str,
    action: str,
    description: Optional[str] = None,
) -> Permission:
    """Create a new permission. Raises ``ValueError`` if it already exists."""
    existing = await get_permission_by_resource_action(db, resource, action)
    if existing:
        raise ValueError(f"Permission '{resource}:{action}' already exists")
    permission = Permission(resource=resource, action=action, description=description)
    db.add(permission)
    await db.flush()
    return permission


async def delete_permission(db: AsyncSession, permission_id: UUID) -> None:
    """Delete a permission. The wildcard ``*:*`` permission cannot be deleted."""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ValueError("Permission not found")
    if permission.resource == "*" and permission.action == "*":
        raise ValueError("The wildcard permission '*:*' cannot be deleted")
    # role_permissions rows cascade on delete
    await db.delete(permission)
    await db.flush()


# ---------------------------------------------------------------------------
# Role-permission management
# ---------------------------------------------------------------------------

async def get_role_permission_ids(db: AsyncSession, role_id: UUID) -> list[UUID]:
    """Return the IDs of all permissions assigned to a role."""
    result = await db.execute(
        select(role_permissions.c.permission_id).where(role_permissions.c.role_id == role_id)
    )
    return [row[0] for row in result.all()]


async def grant_permission(db: AsyncSession, role_id: UUID, permission_id: UUID) -> None:
    """Grant a permission to a role. Idempotent — no-op if already granted."""
    await db.execute(
        sa_insert(role_permissions)
        .values(role_id=role_id, permission_id=permission_id)
        .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
    )
    await db.flush()


async def revoke_permission(db: AsyncSession, role_id: UUID, permission_id: UUID) -> None:
    """Revoke a permission from a role."""
    await db.execute(
        delete(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    )
    await db.flush()


async def set_role_permissions(
    db: AsyncSession, role_id: UUID, permission_ids: list[UUID]
) -> list[UUID]:
    """Replace the full permission set for a role. Returns the final permission IDs."""
    # Remove all existing
    await db.execute(delete(role_permissions).where(role_permissions.c.role_id == role_id))
    # Insert new ones
    for pid in permission_ids:
        await db.execute(
            sa_insert(role_permissions)
            .values(role_id=role_id, permission_id=pid)
            .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
        )
    await db.flush()
    return permission_ids


# ---------------------------------------------------------------------------
# User-role queries
# ---------------------------------------------------------------------------

async def get_user_role_names(db: AsyncSession, user: User) -> list[str]:
    """Return the slugs of all active roles assigned to the user."""
    result = await db.execute(
        select(Role.name)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user.id, Role.is_active.is_(True))
    )
    return sorted(result.scalars().all())


async def user_has_role(db: AsyncSession, user: User, role_name: str) -> bool:
    """Check whether the user has a specific role."""
    result = await db.execute(
        select(user_roles.c.role_id)
        .join(Role, user_roles.c.role_id == Role.id)
        .where(
            user_roles.c.user_id == user.id,
            Role.name == role_name,
            Role.is_active.is_(True),
        )
    )
    return result.first() is not None


# ---------------------------------------------------------------------------
# User-role management
# ---------------------------------------------------------------------------

async def assign_roles(
    db: AsyncSession,
    user: User,
    role_names: list[str],
    assigned_by: Optional[User] = None,
) -> list[str]:
    """Replace the user's role set with ``role_names``.

    - Removes role assignments that are not in ``role_names``.
    - Adds role assignments that are missing.
    - Updates ``active_role_id`` if the current active role was removed.
    - Returns the final list of role slugs.
    """
    # De-duplicate while preserving order
    role_names = list(dict.fromkeys(role_names))
    if not role_names:
        raise ValueError("At least one role is required")

    # Resolve role names to Role records (include inactive roles so we don't
    # accidentally assign a deactivated role)
    result = await db.execute(
        select(Role).where(Role.name.in_(role_names))
    )
    roles = result.scalars().all()
    role_ids = {role.id for role in roles}
    resolved_names = [role.name for role in roles]
    if len(roles) != len(role_names):
        missing = set(role_names) - set(resolved_names)
        raise ValueError(f"Unknown roles: {sorted(missing)}")

    # Only allow active roles to be assigned
    inactive = [r.name for r in roles if not r.is_active]
    if inactive:
        raise ValueError(f"Cannot assign inactive roles: {sorted(inactive)}")

    # Remove stale assignments
    await db.execute(
        delete(user_roles).where(
            user_roles.c.user_id == user.id,
            user_roles.c.role_id.not_in(role_ids) if role_ids else True,
        )
    )

    # Add missing assignments
    for role in roles:
        await db.execute(
            sa_insert(user_roles)
            .values(
                user_id=user.id,
                role_id=role.id,
                assigned_by=assigned_by.id if assigned_by else None,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
        )

    # Sync active_role_id
    if user.active_role_id and user.active_role_id not in role_ids:
        user.active_role_id = next(iter(role_ids))
    elif not user.active_role_id:
        user.active_role_id = next(iter(role_ids))

    await db.flush()
    return resolved_names


async def add_role(
    db: AsyncSession,
    user: User,
    role_name: str,
    assigned_by: Optional[User] = None,
) -> list[str]:
    """Add a single role to the user. Returns the updated role list."""
    current = await get_user_role_names(db, user)
    if role_name not in current:
        current.append(role_name)
    return await assign_roles(db, user, current, assigned_by)


async def remove_role(
    db: AsyncSession,
    user: User,
    role_name: str,
) -> list[str]:
    """Remove a single role from the user. Returns the updated role list.

    Raises ``ValueError`` if the user would be left with zero roles.
    """
    current = await get_user_role_names(db, user)
    if role_name in current:
        current.remove(role_name)
    if not current:
        raise ValueError("Cannot remove the last role from a user")
    return await assign_roles(db, user, current)


async def set_active_role(db: AsyncSession, user: User, role_name: str) -> None:
    """Set the user's active role by slug. Raises if the user doesn't have it."""
    if not await user_has_role(db, user, role_name):
        current = await get_user_role_names(db, user)
        raise ValueError(
            f"User does not have the '{role_name}' role. "
            f"Available roles: {', '.join(current)}"
        )
    role = await get_role_by_name(db, role_name)
    user.active_role_id = role.id
    await db.flush()


async def get_active_role_name(db: AsyncSession, user: User) -> Optional[str]:
    """Return the slug of the user's active role, or None."""
    if not user.active_role_id:
        return None
    result = await db.execute(
        select(Role.name).where(Role.id == user.active_role_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Aggregate helpers for the admin UI
# ---------------------------------------------------------------------------

async def list_roles_with_stats(db: AsyncSession, include_inactive: bool = False) -> list[dict]:
    """Return all roles with user_count and permission_count for the admin table."""
    roles = await list_roles(db, include_inactive=include_inactive)
    result = []
    for role in roles:
        user_count = await count_users_with_role(db, role.id)
        perm_count_result = await db.execute(
            select(func.count())
            .select_from(role_permissions)
            .where(role_permissions.c.role_id == role.id)
        )
        perm_count = perm_count_result.scalar() or 0
        result.append({
            "id": str(role.id),
            "name": role.name,
            "label": role.label,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "user_count": user_count,
            "permission_count": perm_count,
            "created_at": role.created_at.isoformat() if role.created_at else None,
        })
    return result
