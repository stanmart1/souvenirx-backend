"""Pydantic schemas for RBAC role and permission management."""
import uuid
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Permission schemas
# ---------------------------------------------------------------------------

class PermissionResponse(BaseModel):
    id: uuid.UUID
    resource: str
    action: str
    description: str | None = None

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    resource: str = Field(..., min_length=1, max_length=50, description="Resource name (e.g. 'products')")
    action: str = Field(..., min_length=1, max_length=50, description="Action name (e.g. 'write')")
    description: str | None = None


# ---------------------------------------------------------------------------
# Role schemas
# ---------------------------------------------------------------------------

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$",
                      description="Unique slug (lowercase, alphanumeric, underscores)")
    label: str = Field(..., min_length=2, max_length=100, description="Display name")
    description: str | None = None
    is_active: bool = True


class RoleUpdate(BaseModel):
    label: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class PermissionBrief(BaseModel):
    id: uuid.UUID
    resource: str
    action: str
    description: str | None = None


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    label: str
    description: str | None
    is_system: bool
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None
    permissions: list[PermissionBrief] = []
    user_count: int = 0

    model_config = {"from_attributes": True}


class RoleSummary(BaseModel):
    """Lightweight role representation for list views."""
    id: uuid.UUID
    name: str
    label: str
    description: str | None
    is_system: bool
    is_active: bool
    user_count: int = 0
    permission_count: int = 0
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Role-permission management schemas
# ---------------------------------------------------------------------------

class RolePermissionUpdate(BaseModel):
    """Replace the full permission set for a role."""
    permission_ids: list[uuid.UUID]


class RolePermissionAdd(BaseModel):
    """Add a single permission to a role."""
    permission_id: uuid.UUID


# ---------------------------------------------------------------------------
# User-role management schemas
# ---------------------------------------------------------------------------

class UserRoleUpdate(BaseModel):
    """Replace the full role set for a user."""
    roles: list[str]


class UserRoleAdd(BaseModel):
    """Add a single role to a user."""
    role: str
