"""Design template models for product customization"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class DesignTemplate(Base):
    """Pre-designed templates that customers can customize"""
    __tablename__ = "design_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Categorization
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g., "Classic Script", "Bold & Fun", "Elegant Serif", "Handwritten"
    
    style: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "Minimalist", "Vintage", "Modern", "Playful"
    
    tags: Mapped[Optional[list]] = mapped_column(JSONB)
    # e.g., ["wedding", "birthday", "corporate", "motivational"]
    
    # Template design data
    design_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Complete design specification with layers, fonts, colors, etc.
    
    # Preview
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_images: Mapped[Optional[list]] = mapped_column(JSONB)
    # Multiple preview images showing template on different products
    
    # Compatibility
    compatible_products: Mapped[Optional[list]] = mapped_column(JSONB)
    # List of product IDs or categories this template works with
    
    # Pricing
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_price: Mapped[int] = mapped_column(Integer, default=0)
    # Extra charge for premium templates (in kobo)
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    popularity_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator: Mapped["User"] = relationship()
    customer_designs: Mapped[list["CustomerDesign"]] = relationship(back_populates="template")
    
    __table_args__ = (
        Index('idx_template_category_active', 'category', 'is_active'),
        Index('idx_template_popularity', 'popularity_score'),
    )


class CustomerDesign(Base):
    """Customer's customized version of a template"""
    __tablename__ = "customer_designs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("design_templates.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    
    # Design data (modified version of template)
    design_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Preview
    preview_url: Mapped[Optional[str]] = mapped_column(String(500))
    # Generated preview image of the customized design
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # draft, saved, ordered, archived
    
    # Metadata
    name: Mapped[Optional[str]] = mapped_column(String(255))
    # Customer can name their design for later reuse
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship()
    template: Mapped["DesignTemplate"] = relationship(back_populates="customer_designs")
    product: Mapped["Product"] = relationship()
    logo_overlays: Mapped[list["LogoOverlayConfig"]] = relationship(back_populates="customer_design", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_customer_design_user', 'user_id', 'status'),
        Index('idx_customer_design_created', 'created_at'),
    )
