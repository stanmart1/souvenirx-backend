import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"
    affiliate = "affiliate"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(100), default="customer", nullable=False)  # Comma-separated roles: "customer,affiliate,admin"
    active_role: Mapped[Optional[str]] = mapped_column(String(20))  # Current active role for session
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String(255))
    verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tags: Mapped[Optional[str]] = mapped_column(String(500))  # Comma-separated tags for segmentation
    fcm_token: Mapped[Optional[str]] = mapped_column(String(500))  # Firebase Cloud Messaging device token
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    reviews: Mapped[list["Review"]] = relationship(back_populates="user")
    affiliate: Mapped[Optional["Affiliate"]] = relationship(back_populates="user", uselist=False)
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    wishlist_items: Mapped[list["WishlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["UserProject"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    def get_roles(self) -> list[str]:
        """Get list of roles for this user"""
        return [r.strip() for r in self.role.split(",") if r.strip()]
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.get_roles()
    
    def add_role(self, role: str) -> None:
        """Add a role to user if not already present"""
        roles = self.get_roles()
        if role not in roles:
            roles.append(role)
            self.role = ",".join(roles)
    
    def remove_role(self, role: str) -> None:
        """Remove a role from user"""
        roles = self.get_roles()
        if role in roles:
            roles.remove(role)
            self.role = ",".join(roles) if roles else "customer"


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(50), default="Home")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="addresses")
