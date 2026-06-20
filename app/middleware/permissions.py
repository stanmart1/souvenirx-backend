"""Permission-based access control helpers.

This module is the foundation for the new RBAC system described in
docs/RBAC_ARCHITECTURE_PROPOSAL.md. It can be used alongside the existing role-based
middleware during the migration period.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rbac import Permission, Role, role_permissions, user_roles
from app.models.user import User


def require_permission(permission: str):
    """Dependency factory that enforces a single permission on an endpoint.

    Example:
        @router.post(
            "/products",
            dependencies=[Depends(require_permission("products:write"))],
        )
    """
    # Import here to avoid a circular import with app.middleware.auth.
    from app.middleware.auth import get_current_user

    async def checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await user_has_permission(user, permission, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return user

    return checker


async def user_has_permission(user: User, permission: str, db: AsyncSession) -> bool:
    """Check whether a user has a specific permission via the RBAC tables.

    Permission format is ``resource:action``. Wildcards are supported:
    - ``*:*`` grants every permission.
    - ``resource:*`` grants every action on that resource.
    - ``*:action`` grants that action on every resource.
    """
    resource, action = permission.split(":", 1)

    result = await db.execute(
        select(func.count())
        .select_from(user_roles)
        .join(role_permissions, user_roles.c.role_id == role_permissions.c.role_id)
        .join(Permission, role_permissions.c.permission_id == Permission.id)
        .join(Role, user_roles.c.role_id == Role.id)
        .where(
            user_roles.c.user_id == user.id,
            Role.is_active.is_(True),
            Permission.resource.in_([resource, "*"]),
            Permission.action.in_([action, "*"]),
        )
    )
    return result.scalar() > 0


# Re-export the canonical role check from the RBAC service for backwards
# compatibility with callers that import from this module.
from app.services.rbac import user_has_role  # noqa: E402,F401
