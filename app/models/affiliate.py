import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AffiliateStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ConversionStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    referral_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.10)
    cookie_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_earnings: Mapped[int] = mapped_column(Integer, default=0)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100))
    account_number: Mapped[Optional[str]] = mapped_column(String(20))
    account_name: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="affiliate")
    clicks: Mapped[list["AffiliateClick"]] = relationship(back_populates="affiliate", cascade="all, delete-orphan")
    conversions: Mapped[list["AffiliateConversion"]] = relationship(back_populates="affiliate", cascade="all, delete-orphan")
    payouts: Mapped[list["AffiliatePayout"]] = relationship(back_populates="affiliate", cascade="all, delete-orphan")


class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    landing_page: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    affiliate: Mapped["Affiliate"] = relationship(back_populates="clicks")


class AffiliateConversion(Base):
    __tablename__ = "affiliate_conversions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    affiliate: Mapped["Affiliate"] = relationship(back_populates="conversions")
    order: Mapped["Order"] = relationship()


class AffiliatePayout(Base):
    __tablename__ = "affiliate_payouts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(50), default="Bank transfer")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    affiliate: Mapped["Affiliate"] = relationship(back_populates="payouts")
