import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    guest_email = Column(String(255), nullable=True)  # For guest users
    
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Optional attachment
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    
    # Ticket metadata
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.open, nullable=False)
    priority = Column(SQLEnum(TicketPriority), default=TicketPriority.medium, nullable=False)
    category = Column(String(100), nullable=True)  # e.g., "order", "payment", "product", "general"
    
    # Admin response
    admin_response = Column(Text, nullable=True)
    admin_responded_at = Column(DateTime(timezone=True), nullable=True)
    admin_responded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
