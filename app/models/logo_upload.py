import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base


class LogoUploadStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LogoUpload(Base):
    __tablename__ = "logo_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_size = Column(String(50), nullable=False)  # Store as string like "2.5MB"
    mime_type = Column(String(100), nullable=False)
    
    status = Column(SQLEnum(LogoUploadStatus), default=LogoUploadStatus.pending, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
