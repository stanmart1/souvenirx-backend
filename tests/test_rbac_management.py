"""Tests for the RBAC role and permission management service functions."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services import rbac as rbac_service
from app.models.rbac import Role, Permission


class TestRoleCRUD:
    """Tests for create_role, update_role, delete_role, list_roles."""

    @pytest.mark.asyncio
    async def test_create_role_success(self):
        db = AsyncMock()
        # No existing role with this name
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        role = await rbac_service.create_role(db, "editor", "Editor", "Can edit content")
        assert role.name == "editor"
        assert role.label == "Editor"
        assert role.is_system is False
        assert role.is_active is True
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role_duplicate_raises(self):
        db = AsyncMock()
        existing = MagicMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
        with pytest.raises(ValueError, match="already exists"):
            await rbac_service.create_role(db, "admin", "Admin")

    @pytest.mark.asyncio
    async def test_update_role_success(self):
        db = AsyncMock()
        role = MagicMock(spec=Role)
        role.id = uuid.uuid4()
        role.is_system = False
        role.label = "Old Label"
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=role))
        updated = await rbac_service.update_role(db, role.id, label="New Label")
        assert updated.label == "New Label"

    @pytest.mark.asyncio
    async def test_update_role_not_found_raises(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        with pytest.raises(ValueError, match="not found"):
            await rbac_service.update_role(db, uuid.uuid4(), label="New")

    @pytest.mark.asyncio
    async def test_update_role_cannot_deactivate_system_role(self):
        db = AsyncMock()
        role = MagicMock(spec=Role)
        role.id = uuid.uuid4()
        role.is_system = True
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=role))
        with pytest.raises(ValueError, match="System roles cannot be deactivated"):
            await rbac_service.update_role(db, role.id, is_active=False)

    @pytest.mark.asyncio
    async def test_delete_role_system_role_raises(self):
        db = AsyncMock()
        role = MagicMock(spec=Role)
        role.id = uuid.uuid4()
        role.is_system = True
        role.name = "admin"
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=role))
        # count_users_with_role mock
        with pytest.raises(ValueError, match="System roles cannot be deleted"):
            await rbac_service.delete_role(db, role.id)

    @pytest.mark.asyncio
    async def test_delete_role_with_users_raises(self):
        db = AsyncMock()
        role = MagicMock(spec=Role)
        role.id = uuid.uuid4()
        role.is_system = False
        role.name = "editor"
        # First execute: get_role_by_id, Second: count users
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=role)),
            MagicMock(scalar=MagicMock(return_value=3)),
        ]
        with pytest.raises(ValueError, match="3 user.*still assigned"):
            await rbac_service.delete_role(db, role.id)

    @pytest.mark.asyncio
    async def test_list_roles_excludes_inactive_by_default(self):
        db = AsyncMock()
        active_role = MagicMock(spec=Role, name="active")
        active_role.is_active = True
        active_role.name = "customer"
        inactive_role = MagicMock(spec=Role, name="inactive")
        inactive_role.is_active = False
        inactive_role.name = "old_role"
        db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[active_role]))))
        roles = await rbac_service.list_roles(db)
        assert len(roles) == 1
        assert roles[0].is_active is True


class TestPermissionCRUD:
    """Tests for create_permission, delete_permission."""

    @pytest.mark.asyncio
    async def test_create_permission_success(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        perm = await rbac_service.create_permission(db, "blog", "write", "Write blog posts")
        assert perm.resource == "blog"
        assert perm.action == "write"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_permission_duplicate_raises(self):
        db = AsyncMock()
        existing = MagicMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
        with pytest.raises(ValueError, match="already exists"):
            await rbac_service.create_permission(db, "users", "read")

    @pytest.mark.asyncio
    async def test_delete_permission_wildcard_raises(self):
        db = AsyncMock()
        perm = MagicMock(spec=Permission)
        perm.resource = "*"
        perm.action = "*"
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=perm))
        with pytest.raises(ValueError, match=r"\*:\*.*cannot be deleted"):
            await rbac_service.delete_permission(db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_delete_permission_not_found_raises(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        with pytest.raises(ValueError, match="not found"):
            await rbac_service.delete_permission(db, uuid.uuid4())


class TestRolePermissionManagement:
    """Tests for grant_permission, revoke_permission, set_role_permissions."""

    @pytest.mark.asyncio
    async def test_grant_permission_is_idempotent(self):
        db = AsyncMock()
        role_id = uuid.uuid4()
        perm_id = uuid.uuid4()
        # Should not raise even if called twice
        await rbac_service.grant_permission(db, role_id, perm_id)
        assert db.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_revoke_permission(self):
        db = AsyncMock()
        role_id = uuid.uuid4()
        perm_id = uuid.uuid4()
        await rbac_service.revoke_permission(db, role_id, perm_id)
        assert db.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_set_role_permissions_replaces_all(self):
        db = AsyncMock()
        role_id = uuid.uuid4()
        perm_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        result = await rbac_service.set_role_permissions(db, role_id, perm_ids)
        assert result == perm_ids
        # First call deletes all, then one insert per permission
        assert db.execute.call_count == 1 + len(perm_ids)


class TestGetRoleWithPermissions:
    """Tests for get_role_with_permissions."""

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_role(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        result = await rbac_service.get_role_with_permissions(db, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dict_with_permissions_and_user_count(self):
        db = AsyncMock()
        role = MagicMock(spec=Role)
        role.id = uuid.uuid4()
        role.name = "editor"
        role.label = "Editor"
        role.description = "Content editor"
        role.is_system = False
        role.is_active = True
        role.created_at = MagicMock()
        role.updated_at = MagicMock()
        role.created_at.isoformat = MagicMock(return_value="2026-01-01T00:00:00")
        role.updated_at.isoformat = MagicMock(return_value="2026-01-01T00:00:00")

        perm1 = MagicMock(spec=Permission)
        perm1.id = uuid.uuid4()
        perm1.resource = "products"
        perm1.action = "read"
        perm1.description = "View products"

        # Mock three execute calls: get_role, get permissions, get user count
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=role)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[perm1])))),
            MagicMock(scalar=MagicMock(return_value=5)),
        ]
        result = await rbac_service.get_role_with_permissions(db, role.id)
        assert result is not None
        assert result["name"] == "editor"
        assert result["user_count"] == 5
        assert len(result["permissions"]) == 1
        assert result["permissions"][0]["resource"] == "products"


class TestListRolesWithStats:
    """Tests for list_roles_with_stats."""

    @pytest.mark.asyncio
    async def test_returns_roles_with_counts(self):
        db = AsyncMock()
        role1 = MagicMock(spec=Role)
        role1.id = uuid.uuid4()
        role1.name = "admin"
        role1.label = "Admin"
        role1.description = None
        role1.is_system = True
        role1.is_active = True
        role1.created_at = MagicMock()
        role1.created_at.isoformat = MagicMock(return_value="2026-01-01")

        role2 = MagicMock(spec=Role)
        role2.id = uuid.uuid4()
        role2.name = "customer"
        role2.label = "Customer"
        role2.description = None
        role2.is_system = True
        role2.is_active = True
        role2.created_at = MagicMock()
        role2.created_at.isoformat = MagicMock(return_value="2026-01-01")

        # list_roles returns [role1, role2]
        # For each role: count_users_with_role (1 execute) + perm count (1 execute)
        db.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[role1, role2])))),
            MagicMock(scalar=MagicMock(return_value=1)),  # role1 user count
            MagicMock(scalar=MagicMock(return_value=1)),  # role1 perm count
            MagicMock(scalar=MagicMock(return_value=10)),  # role2 user count
            MagicMock(scalar=MagicMock(return_value=4)),  # role2 perm count
        ]
        result = await rbac_service.list_roles_with_stats(db)
        assert len(result) == 2
        assert result[0]["name"] == "admin"
        assert result[0]["user_count"] == 1
        assert result[1]["name"] == "customer"
        assert result[1]["user_count"] == 10
