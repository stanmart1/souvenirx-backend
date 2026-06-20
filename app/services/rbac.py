"""RBAC role-management service.

This module is the single source of truth for assigning and removing roles
on users. All role mutations should go through these helpers so that the
``user_roles`` table, ``active_role_id``, and the ``Affiliate`` record stay
in sync.
"""

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as sa_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Role, user_roles
from app.models.user import User


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    """Fetch a role by its unique slug."""
    result = await db.execute(select(Role).where(Role.name == name, Role.is_active.is_(True)))
    return result.scalar_one_or_none()


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

    # Resolve role names to Role records
    result = await db.execute(
        select(Role).where(Role.name.in_(role_names), Role.is_active.is_(True))
    )
    roles = result.scalars().all()
    role_ids = {role.id for role in roles}
    resolved_names = [role.name for role in roles]
    if len(roles) != len(role_names):
        missing = set(role_names) - set(resolved_names)
        raise ValueError(f"Unknown or inactive roles: {sorted(missing)}")

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
