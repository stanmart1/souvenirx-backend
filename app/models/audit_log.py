"""Audit log model for tracking admin actions"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AuditLog(Base):
    """Audit log for tracking administrative actions"""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "update_customer", "reset_password"
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "user", "order", "product"
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)  # UUID or ID of the resource
    changes: Mapped[Optional[str]] = mapped_column(Text)  # JSON string of before/after changes
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv4 or IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to admin user
    admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[admin_id])
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type}:{self.resource_id})>"
