import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.middleware.permissions import user_has_permission, user_has_role
from app.models.rbac import Permission, Role, role_permissions, user_roles


class TestUserHasPermission:
    @pytest.mark.asyncio
    async def test_returns_true_when_user_has_exact_permission(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = 1
        db.execute.return_value = result

        assert await user_has_permission(user, "orders:read", db) is True

        # Verify the query filters by the correct resource and action
        call = db.execute.call_args[0][0]
        compiled = str(call.compile(compile_kwargs={"literal_binds": True}))
        assert "orders" in compiled
        assert "read" in compiled

    @pytest.mark.asyncio
    async def test_returns_true_with_wildcard_permission(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = 1
        db.execute.return_value = result

        assert await user_has_permission(user, "anything:delete", db) is True

        call = db.execute.call_args[0][0]
        compiled = str(call.compile(compile_kwargs={"literal_binds": True}))
        assert "'*'" in compiled

    @pytest.mark.asyncio
    async def test_returns_false_when_user_has_no_permission(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = 0
        db.execute.return_value = result

        assert await user_has_permission(user, "orders:delete", db) is False


class TestUserHasRole:
    @pytest.mark.asyncio
    async def test_returns_true_when_user_has_active_role(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = 1
        db.execute.return_value = result

        assert await user_has_role(user, "admin", db) is True

        call = db.execute.call_args[0][0]
        compiled = str(call.compile(compile_kwargs={"literal_binds": True}))
        assert "admin" in compiled

    @pytest.mark.asyncio
    async def test_returns_false_when_user_does_not_have_role(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = 0
        db.execute.return_value = result

        assert await user_has_role(user, "admin", db) is False
