import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class StockNotification(Base):
    __tablename__ = "stock_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    guest_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_stock_notification_user_product"),
        Index("ix_stock_notifications_product_id", "product_id"),
        Index("ix_stock_notifications_guest_email", "guest_email"),
    )
