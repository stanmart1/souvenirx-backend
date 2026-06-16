import uuid
import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class OrderStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    in_production = "in_production"
    shipped = "shipped"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    awaiting_verification = "awaiting_verification"


class PaymentGateway(str, enum.Enum):
    paystack = "paystack"
    flutterwave = "flutterwave"
    bank_transfer = "bank_transfer"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_zone: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=False)
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_fee: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    payment_gateway: Mapped[Optional[str]] = mapped_column(String(20))
    payment_ref: Mapped[Optional[str]] = mapped_column(String(255))
    payment_status: Mapped[str] = mapped_column(String(30), default="pending")
    bank_transfer_proof_url: Mapped[Optional[str]] = mapped_column(String(500))
    promo_code: Mapped[Optional[str]] = mapped_column(String(50))
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    event_date: Mapped[Optional[date]] = mapped_column(Date)
    estimated_delivery: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    tracking: Mapped[list["OrderTracking"]] = relationship(back_populates="order", cascade="all, delete-orphan", order_by="OrderTracking.created_at")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    customization: Mapped[Optional[dict]] = mapped_column(JSONB)
    customer_design_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_designs.id", ondelete="SET NULL"))
    design_preview_url: Mapped[Optional[str]] = mapped_column(String(500))

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
    customer_design: Mapped[Optional["CustomerDesign"]] = relationship()


class OrderTracking(Base):
    __tablename__ = "order_tracking"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="tracking")
