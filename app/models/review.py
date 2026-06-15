import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Media support
    media_url: Mapped[Optional[str]] = mapped_column(String(500))  # URL to uploaded image/video
    media_type: Mapped[Optional[str]] = mapped_column(String(20))  # 'image' or 'video'
    
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Moderation
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto-approve by default
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="reviews")
    user: Mapped[Optional["User"]] = relationship(back_populates="reviews")
