"""RBAC synchronization helpers.

These helpers keep the legacy comma-separated `User.role` column and the new
relational RBAC tables in sync during the migration period.
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


async def sync_user_roles_from_legacy(db: AsyncSession, user: User) -> None:
    """Sync the `user_roles` table and `active_role_id` from the legacy role string.

    Should be called after any code that mutates `user.role` or `user.active_role`.
    """
    legacy_roles = user.get_roles()
    if not legacy_roles:
        # Ensure every user has at least the customer role
        legacy_roles = ["customer"]
        user.role = "customer"

    # Resolve role names to IDs
    result = await db.execute(select(Role).where(Role.name.in_(legacy_roles), Role.is_active.is_(True)))
    roles = result.scalars().all()
    role_ids = {role.id for role in roles}

    # Remove any stale assignments
    await db.execute(
        delete(user_roles).where(
            user_roles.c.user_id == user.id,
            user_roles.c.role_id.not_in(role_ids) if role_ids else True,
        )
    )

    # Add missing assignments (ignore conflicts)
    for role_id in role_ids:
        await db.execute(
            sa_insert(user_roles)
            .values(user_id=user.id, role_id=role_id)
            .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
        )

    # Sync active_role_id from active_role string
    if user.active_role:
        active_role = await get_role_by_name(db, user.active_role)
        user.active_role_id = active_role.id if active_role else None
    elif role_ids:
        # Default to first available role if active_role is unset
        user.active_role_id = next(iter(role_ids))
    else:
        user.active_role_id = None
