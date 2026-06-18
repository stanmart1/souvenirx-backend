"""Design font catalogue used by the product customisation flow."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DesignFont(Base):
    """A font exposed to the customisation UI (Google Fonts or custom upload)."""

    __tablename__ = "design_fonts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # script | serif | sans-serif | handwritten | display | monospace
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # google | custom
    file_url: Mapped[Optional[str]] = mapped_column(String(500))
    preview_text: Mapped[str] = mapped_column(
        String(120), nullable=False, default="AaBbCc 123"
    )
    sample_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_design_fonts_active_order", "is_active", "sort_order"),
    )
