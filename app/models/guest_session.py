import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Store temporary cart data as JSON
    cart_data = Column(Text, nullable=True)
    
    # Track if guest converted to registered user
    converted_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
