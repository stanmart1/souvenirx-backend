import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base


class NotificationType(str, Enum):
    order_status = "order_status"
    payment = "payment"
    delivery = "delivery"
    promotion = "promotion"
    system = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Optional link to related resource
    link = Column(String(500), nullable=True)
    link_text = Column(String(100), nullable=True)
    
    # Metadata as JSON for additional data
    meta_data = Column(Text, nullable=True)
    
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
