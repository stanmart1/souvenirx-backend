"""Verify the RBAC tables were created and seeded correctly."""
import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rbac import Permission, Role, user_roles
from app.models.user import User


async def verify():
    async for db in get_db():
        db: AsyncSession

        roles_count = (await db.execute(select(func.count()).select_from(Role))).scalar()
        perms_count = (await db.execute(select(func.count()).select_from(Permission))).scalar()
        user_roles_count = (await db.execute(select(func.count()).select_from(user_roles))).scalar()
        users_with_active_role = (
            await db.execute(select(func.count()).where(User.active_role_id.is_not(None)))
        ).scalar()

        print(f"roles: {roles_count}")
        print(f"permissions: {perms_count}")
        print(f"user_roles assignments: {user_roles_count}")
        print(f"users with active_role_id: {users_with_active_role}")

        system_roles = (await db.execute(select(Role.name).where(Role.is_system.is_(True)))).scalars().all()
        print(f"system roles: {sorted(system_roles)}")
        break


if __name__ == "__main__":
    asyncio.run(verify())
