"""Logo upload and overlay models"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, Boolean, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class LogoUpload(Base):
    """Customer uploaded logos with processing metadata"""
    __tablename__ = "logo_uploads"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User reference
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File information
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)  # png, jpg, svg, webp
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Image dimensions
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Processed versions
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))
    # Small preview (200x200)
    
    optimized_url: Mapped[Optional[str]] = mapped_column(String(500))
    # Optimized for web (max 1000x1000)
    
    transparent_url: Mapped[Optional[str]] = mapped_column(String(500))
    # Background removed version (if applicable)
    
    # Processing metadata
    has_transparency: Mapped[bool] = mapped_column(Boolean, default=False)
    dominant_colors: Mapped[Optional[list]] = mapped_column(JSONB)
    # ["#FFFFFF", "#000000", "#FF0000"]
    
    is_vector: Mapped[bool] = mapped_column(Boolean, default=False)
    # True for SVG files
    
    processing_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending, processing, completed, failed
    
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Organization
    name: Mapped[Optional[str]] = mapped_column(String(255))
    # User-friendly name for the logo
    
    tags: Mapped[Optional[list]] = mapped_column(JSONB)
    # ["company", "personal", "event"]
    
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # active, archived, deleted
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship()
    overlays: Mapped[list["LogoOverlayConfig"]] = relationship(back_populates="logo_upload", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_logo_upload_user_status', 'user_id', 'status'),
        Index('idx_logo_upload_created', 'created_at'),
    )


class LogoOverlayConfig(Base):
    """Configuration for how a logo is positioned on a product"""
    __tablename__ = "logo_overlay_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    customer_design_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_designs.id", ondelete="CASCADE"), nullable=False)
    logo_upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logo_uploads.id", ondelete="CASCADE"), nullable=False)
    
    # Position (relative to canvas, 0-1 range)
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    # 0 = left edge, 0.5 = center, 1 = right edge
    
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    # 0 = top edge, 0.5 = center, 1 = bottom edge
    
    # Size (relative to canvas, 0-1 range)
    scale: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    # 0.2 = 20% of canvas size
    
    # Rotation
    rotation: Mapped[float] = mapped_column(Float, default=0.0)
    # Degrees, 0-360
    
    # Effects
    opacity: Mapped[float] = mapped_column(Float, default=1.0)
    # 0.0 = transparent, 1.0 = opaque
    
    flip_horizontal: Mapped[bool] = mapped_column(Boolean, default=False)
    flip_vertical: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Filters
    brightness: Mapped[float] = mapped_column(Float, default=1.0)
    # 0.5 = darker, 1.0 = normal, 1.5 = brighter
    
    contrast: Mapped[float] = mapped_column(Float, default=1.0)
    saturation: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Color adjustments
    color_overlay: Mapped[Optional[str]] = mapped_column(String(7))
    # Hex color for tinting, e.g., "#FF0000"
    
    color_overlay_opacity: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Background
    remove_background: Mapped[bool] = mapped_column(Boolean, default=False)
    background_color: Mapped[Optional[str]] = mapped_column(String(7))
    # Replacement background color if removed
    
    # Border/Shadow
    border_width: Mapped[int] = mapped_column(Integer, default=0)
    border_color: Mapped[Optional[str]] = mapped_column(String(7))
    
    shadow_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    shadow_blur: Mapped[int] = mapped_column(Integer, default=10)
    shadow_offset_x: Mapped[int] = mapped_column(Integer, default=5)
    shadow_offset_y: Mapped[int] = mapped_column(Integer, default=5)
    shadow_color: Mapped[str] = mapped_column(String(9), default="#00000080")
    # RGBA hex
    
    # Layer order
    z_index: Mapped[int] = mapped_column(Integer, default=0)
    # Higher = on top
    
    # Constraints
    lock_aspect_ratio: Mapped[bool] = mapped_column(Boolean, default=True)
    min_scale: Mapped[float] = mapped_column(Float, default=0.05)
    max_scale: Mapped[float] = mapped_column(Float, default=0.8)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer_design: Mapped["CustomerDesign"] = relationship(back_populates="logo_overlays")
    logo_upload: Mapped["LogoUpload"] = relationship(back_populates="overlays")
    
    __table_args__ = (
        Index('idx_logo_overlay_design', 'customer_design_id'),
        Index('idx_logo_overlay_z_index', 'customer_design_id', 'z_index'),
    )


class ProductMockupTemplate(Base):
    """Mockup templates for previewing designs on products"""
    __tablename__ = "product_mockup_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Mockup information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g., "Front View", "Back View", "Angled View"
    
    mockup_image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    # Base product image
    
    # Design area definition
    design_area: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "x": 100, "y": 100,  # Top-left corner in pixels
    #   "width": 800, "height": 800,  # Design area size
    #   "rotation": 0,  # If design area is rotated
    #   "perspective": {  # For 3D mockups (optional)
    #     "topLeft": [x, y],
    #     "topRight": [x, y],
    #     "bottomLeft": [x, y],
    #     "bottomRight": [x, y]
    #   }
    # }
    
    # View type
    view_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # front, back, side, angled, flat
    
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    # Primary view shown first
    
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product: Mapped["Product"] = relationship()
    
    __table_args__ = (
        Index('idx_mockup_product', 'product_id', 'is_primary'),
        Index('idx_mockup_sort', 'product_id', 'sort_order'),
    )
