import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.models.user import User
from app.models.affiliate import Affiliate, AffiliateStatus
from app.routes.admin import _role_match_clause, _sync_affiliate_record


class TestRoleMatchClause:
    """Verify exact matching of comma-separated roles in the user list filter."""

    def test_generates_exact_role_clauses(self):
        clause = _role_match_clause(User.role, "affiliate")
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))

        assert "users.role = 'affiliate'" in compiled
        assert "users.role LIKE 'affiliate,%'" in compiled
        assert "users.role LIKE '%,affiliate,%'" in compiled
        assert "users.role LIKE '%,affiliate'" in compiled

    def test_does_not_use_substring_match(self):
        clause = _role_match_clause(User.role, "affiliate")
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))

        # The old implementation used LIKE '%affiliate%', which would also match
        # a bogus role like 'superaffiliate'. Make sure we no longer do that.
        assert "LIKE '%affiliate%'" not in compiled


class TestSyncAffiliateRecord:
    """Verify the Affiliate record is created, activated, or suspended correctly."""

    @pytest.mark.asyncio
    async def test_creates_affiliate_record_when_role_added(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value = self._scalar_result(None)

        await _sync_affiliate_record(db, user, ["customer", "affiliate"])

        added = db.add.call_args[0][0]
        assert isinstance(added, Affiliate)
        assert added.user_id == user.id
        assert added.status == AffiliateStatus.active.value
        assert added.commission_rate == 0.10
        assert len(added.referral_code) > 0

    @pytest.mark.asyncio
    async def test_reactivates_existing_suspended_affiliate_record(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        affiliate = Affiliate(
            user_id=user.id,
            referral_code="OLD123",
            status=AffiliateStatus.suspended.value,
        )

        db = AsyncMock()
        db.execute.return_value = self._scalar_result(affiliate)

        await _sync_affiliate_record(db, user, ["customer", "affiliate"])

        assert affiliate.status == AffiliateStatus.active.value
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_leaves_active_affiliate_record_unchanged(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        affiliate = Affiliate(
            user_id=user.id,
            referral_code="OLD123",
            status=AffiliateStatus.active.value,
        )

        db = AsyncMock()
        db.execute.return_value = self._scalar_result(affiliate)

        await _sync_affiliate_record(db, user, ["customer", "affiliate"])

        assert affiliate.status == AffiliateStatus.active.value
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_suspends_affiliate_record_when_role_removed(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        affiliate = Affiliate(
            user_id=user.id,
            referral_code="OLD123",
            status=AffiliateStatus.active.value,
        )

        db = AsyncMock()
        db.execute.return_value = self._scalar_result(affiliate)

        await _sync_affiliate_record(db, user, ["customer"])

        assert affiliate.status == AffiliateStatus.suspended.value

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_affiliate_record_and_role_removed(self):
        user = MagicMock()
        user.id = uuid.uuid4()

        db = AsyncMock()
        db.execute.return_value = self._scalar_result(None)

        await _sync_affiliate_record(db, user, ["customer"])

        db.add.assert_not_called()

    def _scalar_result(self, value):
        result = MagicMock()
        result.scalar_one_or_none.return_value = value
        return result

