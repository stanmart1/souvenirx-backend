import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SavedPaymentMethod(Base):
    __tablename__ = "saved_payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Payment gateway token (never store actual card data)
    payment_token: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_gateway: Mapped[str] = mapped_column(String(50), nullable=False)  # 'paystack', 'flutterwave', etc.
    
    # Display information only (safe to store)
    card_last4: Mapped[str] = mapped_column(String(4))
    card_brand: Mapped[str] = mapped_column(String(20))  # 'visa', 'mastercard', etc.
    expiry_month: Mapped[int] = mapped_column()
    expiry_year: Mapped[int] = mapped_column()
    
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
