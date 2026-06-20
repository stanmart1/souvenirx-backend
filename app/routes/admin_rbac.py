"""Admin API routes for RBAC role and permission management.

All endpoints require ``roles:read`` or ``roles:write`` permission.
Mutations are audit-logged.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_admin
from app.middleware.permissions import require_permission
from app.models.user import User
from app.schemas.rbac import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RolePermissionAdd,
    RolePermissionUpdate,
    RoleResponse,
    RoleUpdate,
    UserRoleAdd,
    UserRoleUpdate,
)
from app.services import rbac as rbac_service
from app.services.audit import get_client_ip, get_user_agent, log_audit

router = APIRouter(tags=["RBAC Management"])


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    include_inactive: bool = False,
    admin: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles with permission and user counts."""
    roles = await rbac_service.list_roles_with_stats(db, include_inactive=include_inactive)
    # Fetch permissions for each role
    result = []
    for r in roles:
        role_id = uuid.UUID(r["id"])
        detail = await rbac_service.get_role_with_permissions(db, role_id)
        if detail:
            result.append(detail)
    return result


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreate,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new custom role."""
    try:
        role = await rbac_service.create_role(
            db,
            name=body.name,
            label=body.label,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="create_role",
        resource_type="role",
        resource_id=str(role.id),
        changes={"name": role.name, "label": role.label},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    detail = await rbac_service.get_role_with_permissions(db, role.id)
    return detail


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    admin: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single role with its permissions and user count."""
    detail = await rbac_service.get_role_with_permissions(db, role_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Role not found")
    return detail


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update a role's label, description, or active status."""
    existing = await rbac_service.get_role_with_permissions(db, role_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Role not found")

    try:
        role = await rbac_service.update_role(
            db,
            role_id,
            label=body.label,
            description=body.description,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="update_role",
        resource_type="role",
        resource_id=str(role.id),
        changes={
            "old": {"label": existing["label"], "description": existing["description"], "is_active": existing["is_active"]},
            "new": {"label": role.label, "description": role.description, "is_active": role.is_active},
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    detail = await rbac_service.get_role_with_permissions(db, role.id)
    return detail


@router.delete("/roles/{role_id}", status_code=status.HTTP_200_OK)
async def delete_role(
    role_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom role. System roles and roles with users cannot be deleted."""
    existing = await rbac_service.get_role_with_permissions(db, role_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Role not found")

    try:
        await rbac_service.delete_role(db, role_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="delete_role",
        resource_type="role",
        resource_id=str(role_id),
        changes={"deleted_role": existing["name"]},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return {"message": f"Role '{existing['name']}' deleted successfully"}


# ---------------------------------------------------------------------------
# Role → Permission management
# ---------------------------------------------------------------------------

@router.get("/roles/{role_id}/permissions", response_model=list[PermissionResponse])
async def list_role_permissions(
    role_id: uuid.UUID,
    admin: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """List all permissions assigned to a role."""
    role = await rbac_service.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    detail = await rbac_service.get_role_with_permissions(db, role_id)
    return detail["permissions"] if detail else []


@router.put("/roles/{role_id}/permissions", response_model=list[PermissionResponse])
async def replace_role_permissions(
    role_id: uuid.UUID,
    body: RolePermissionUpdate,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Replace the full permission set for a role."""
    role = await rbac_service.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    old_perm_ids = await rbac_service.get_role_permission_ids(db, role_id)

    try:
        await rbac_service.set_role_permissions(db, role_id, body.permission_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="replace_role_permissions",
        resource_type="role",
        resource_id=str(role_id),
        changes={
            "old_permission_ids": [str(pid) for pid in old_perm_ids],
            "new_permission_ids": [str(pid) for pid in body.permission_ids],
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    detail = await rbac_service.get_role_with_permissions(db, role_id)
    return detail["permissions"] if detail else []


@router.post("/roles/{role_id}/permissions", response_model=list[PermissionResponse])
async def add_role_permission(
    role_id: uuid.UUID,
    body: RolePermissionAdd,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Grant a single permission to a role."""
    role = await rbac_service.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    permission = await rbac_service.get_permission_by_id(db, body.permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await rbac_service.grant_permission(db, role_id, body.permission_id)

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="grant_permission",
        resource_type="role",
        resource_id=str(role_id),
        changes={"permission": f"{permission.resource}:{permission.action}"},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    detail = await rbac_service.get_role_with_permissions(db, role_id)
    return detail["permissions"] if detail else []


@router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=list[PermissionResponse])
async def revoke_role_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a single permission from a role."""
    role = await rbac_service.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    permission = await rbac_service.get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await rbac_service.revoke_permission(db, role_id, permission_id)

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="revoke_permission",
        resource_type="role",
        resource_id=str(role_id),
        changes={"permission": f"{permission.resource}:{permission.action}"},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    detail = await rbac_service.get_role_with_permissions(db, role_id)
    return detail["permissions"] if detail else []


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    admin: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """List all permissions ordered by resource then action."""
    perms = await rbac_service.list_permissions(db)
    return perms


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    body: PermissionCreate,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new custom permission."""
    try:
        permission = await rbac_service.create_permission(
            db,
            resource=body.resource,
            action=body.action,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="create_permission",
        resource_type="permission",
        resource_id=str(permission.id),
        changes={"resource": permission.resource, "action": permission.action},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return permission


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_200_OK)
async def delete_permission(
    permission_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_permission("roles:write")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom permission. The wildcard ``*:*`` cannot be deleted."""
    permission = await rbac_service.get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    try:
        await rbac_service.delete_permission(db, permission_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="delete_permission",
        resource_type="permission",
        resource_id=str(permission_id),
        changes={"deleted": f"{permission.resource}:{permission.action}"},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return {"message": f"Permission '{permission.resource}:{permission.action}' deleted successfully"}


# ---------------------------------------------------------------------------
# User → Role management (consolidated RESTful resource)
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}/roles", response_model=list[RoleResponse])
async def list_user_roles(
    user_id: uuid.UUID,
    admin: User = Depends(require_permission("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles assigned to a user, with permissions."""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_names = await rbac_service.get_user_role_names(db, user)
    roles = []
    for name in role_names:
        role = await rbac_service.get_role_by_name(db, name)
        if role:
            detail = await rbac_service.get_role_with_permissions(db, role.id)
            if detail:
                roles.append(detail)
    return roles


@router.put("/users/{user_id}/roles", response_model=list[str])
async def replace_user_roles(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    request: Request,
    admin: User = Depends(require_permission("roles:assign")),
    db: AsyncSession = Depends(get_db),
):
    """Replace the full role set for a user."""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing admin role from yourself
    if str(user.id) == str(admin.id) and "admin" not in body.roles:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove admin role from your own account",
        )

    old_roles = await rbac_service.get_user_role_names(db, user)
    try:
        new_roles = await rbac_service.assign_roles(db, user, body.roles, assigned_by=admin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Sync affiliate record
    from app.routes.admin import _sync_affiliate_record
    await _sync_affiliate_record(db, user, new_roles)

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="replace_user_roles",
        resource_type="user",
        resource_id=str(user_id),
        changes={"old_roles": old_roles, "new_roles": new_roles},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return new_roles


@router.post("/users/{user_id}/roles", response_model=list[str])
async def add_user_role(
    user_id: uuid.UUID,
    body: UserRoleAdd,
    request: Request,
    admin: User = Depends(require_permission("roles:assign")),
    db: AsyncSession = Depends(get_db),
):
    """Add a single role to a user."""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_roles = await rbac_service.get_user_role_names(db, user)
    try:
        new_roles = await rbac_service.add_role(db, user, body.role, assigned_by=admin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Sync affiliate record
    from app.routes.admin import _sync_affiliate_record
    await _sync_affiliate_record(db, user, new_roles)

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="add_user_role",
        resource_type="user",
        resource_id=str(user_id),
        changes={"added_role": body.role, "all_roles": new_roles},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return new_roles


@router.delete("/users/{user_id}/roles/{role_name}", response_model=list[str])
async def remove_user_role(
    user_id: uuid.UUID,
    role_name: str,
    request: Request,
    admin: User = Depends(require_permission("roles:assign")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a single role from a user."""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing admin role from yourself
    if str(user.id) == str(admin.id) and role_name == "admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot remove admin role from your own account",
        )

    old_roles = await rbac_service.get_user_role_names(db, user)
    try:
        new_roles = await rbac_service.remove_role(db, user, role_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Sync affiliate record
    from app.routes.admin import _sync_affiliate_record
    await _sync_affiliate_record(db, user, new_roles)

    await log_audit(
        db=db,
        admin_id=str(admin.id),
        action="remove_user_role",
        resource_type="user",
        resource_id=str(user_id),
        changes={"removed_role": role_name, "all_roles": new_roles},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    return new_roles
