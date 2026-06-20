import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


# Association table: users <-> roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_by", UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("assigned_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


# Association table: roles <-> permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    """A single access grant on a resource/action pair.

    Examples:
        - users:read
        - orders:write
        - affiliates:approve
    """

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permission_resource_action"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )


class Role(Base):
    """A named collection of permissions.

    System roles (is_system=True) are seeded by the application and cannot be
    deleted. Custom roles can be created by admins from the admin dashboard.
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        primaryjoin="Role.id == user_roles.c.role_id",
        secondaryjoin="User.id == user_roles.c.user_id",
        foreign_keys=[user_roles.c.user_id, user_roles.c.role_id],
    )

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if this role grants a specific permission.

        Supports wildcard matching: resource '*' or action '*' grants all
        permissions on that dimension.
        """
        for permission in self.permissions:
            if permission.resource == "*" or permission.action == "*":
                return True
            if permission.resource == resource and permission.action == action:
                return True
        return False


# Import User at the bottom to avoid circular import issues at module load time.
from app.models.user import User

User.roles = relationship(
    "Role",
    secondary=user_roles,
    back_populates="users",
    lazy="selectin",
    primaryjoin="User.id == user_roles.c.user_id",
    secondaryjoin="Role.id == user_roles.c.role_id",
    foreign_keys=[user_roles.c.user_id, user_roles.c.role_id],
)
