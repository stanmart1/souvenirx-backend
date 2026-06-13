from typing import Optional
from sqlalchemy import String, Integer, Boolean, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # Geographic coverage - hierarchical support
    countries: Mapped[list[str]] = mapped_column(JSONB, nullable=False)  # ["Nigeria", "Ghana", "Benin"]
    states: Mapped[list[str]] = mapped_column(JSONB, nullable=False)  # ["Lagos", "Accra", "Cotonou"]
    lgas: Mapped[list[str]] = mapped_column(JSONB, default=list)  # ["Ikeja", "Ashiamu", "Lagos Island"]
    
    # Zone type
    zone_type: Mapped[str] = mapped_column(String(20), default="state")  # "country", "state", "lga", "custom"
    
    standard_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    express_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    eta_text: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Dynamic pricing
    free_shipping_threshold: Mapped[int] = mapped_column(Integer, default=0)  # Free shipping above this amount
    weight_fee_per_kg: Mapped[int] = mapped_column(Integer, default=0)  # Additional fee per kg
    volume_fee_per_unit: Mapped[int] = mapped_column(Integer, default=0)  # Additional fee per unit
    
    # Delivery time estimation
    min_days: Mapped[int] = mapped_column(Integer, default=3)
    max_days: Mapped[int] = mapped_column(Integer, default=7)
    
    # International shipping
    is_international: Mapped[bool] = mapped_column(Boolean, default=False)
    customs_handling_fee: Mapped[int] = mapped_column(Integer, default=0)
    border_crossing_fee: Mapped[int] = mapped_column(Integer, default=0)
    
    # Automation
    default_carrier: Mapped[Optional[str]] = mapped_column(String(50))  # Default carrier for this zone
    auto_assign: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto-assign to orders


class ShippingMethod(Base):
    __tablename__ = "shipping_methods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255))
    base_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Dynamic pricing rules
    free_above_amount: Mapped[int] = mapped_column(Integer, default=0)
    fee_per_kg: Mapped[int] = mapped_column(Integer, default=0)
    fee_per_item: Mapped[int] = mapped_column(Integer, default=0)
    
    # Delivery time
    min_days: Mapped[int] = mapped_column(Integer, default=3)
    max_days: Mapped[int] = mapped_column(Integer, default=7)
    
    # Automation
    carrier: Mapped[Optional[str]] = mapped_column(String(50))  # Associated carrier
    auto_select_for_zones: Mapped[list[int]] = mapped_column(JSONB, default=list)  # Auto-select for these zones
    max_weight_kg: Mapped[Optional[float]] = mapped_column(Float)  # Max weight for this method
    max_items: Mapped[Optional[int]] = mapped_column(Integer)  # Max items for this method


class ShippingCarrier(Base):
    __tablename__ = "shipping_carriers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # e.g., "dhl", "fedex", "gokada"
    api_key: Mapped[Optional[str]] = mapped_column(String(255))  # Encrypted API key
    api_secret: Mapped[Optional[str]] = mapped_column(String(255))  # Encrypted API secret
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Automation settings
    auto_create_labels: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_schedule_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_track_shipments: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShippingAutomationRule(Base):
    __tablename__ = "shipping_automation_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "auto_zone", "auto_method", "auto_carrier"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    
    # Rule conditions
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)  # { "min_order_value": 50000, "max_weight": 10 }
    actions: Mapped[dict] = mapped_column(JSONB, nullable=False)  # { "assign_zone_id": 1, "assign_method_id": 2 }
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
