"""Quick integration check for the new /api/auth/me/permissions endpoint logic."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.middleware.permissions import user_has_permission
from app.models.rbac import Permission, Role, role_permissions, user_roles


async def test():
    async for db in get_db():
        db: AsyncSession

        # Pick the first admin user
        result = await db.execute(
            select(User)
            .where(User.role.contains("admin"))
            .limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            print("No admin user found to test with")
            break

        print(f"Testing user: {user.email} (role={user.role})")
        print(f"  has_permission('*:*') -> {await user_has_permission(user, '*:*', db)}")
        print(f"  has_permission('users:read') -> {await user_has_permission(user, 'users:read', db)}")
        print(f"  has_permission('orders:write') -> {await user_has_permission(user, 'orders:write', db)}")

        # List effective permissions
        rows = await db.execute(
            select(Permission.resource, Permission.action)
            .join(role_permissions, Permission.id == role_permissions.c.permission_id)
            .join(user_roles, role_permissions.c.role_id == user_roles.c.role_id)
            .join(Role, role_permissions.c.role_id == Role.id)
            .where(
                user_roles.c.user_id == user.id,
                Role.is_active.is_(True),
            )
            .distinct()
        )
        perms = sorted({f"{r}:{a}" for r, a in rows.all()})
        print(f"  effective permissions ({len(perms)}): {perms[:10]}{'...' if len(perms) > 10 else ''}")
        break


if __name__ == "__main__":
    asyncio.run(test())
