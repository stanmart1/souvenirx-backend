from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    qty: int = Field(ge=1)
    customization: Optional[dict[str, Any]] = None
    logo_url: Optional[str] = None


class CartItemUpdate(BaseModel):
    qty: Optional[int] = Field(default=None, ge=1)
    customization: Optional[dict[str, Any]] = None
    logo_url: Optional[str] = None


class OrderCreate(BaseModel):
    customer_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    delivery_zone: Optional[str] = "Lagos Mainland"
    delivery_method: Optional[str] = "standard"
    promo_code: Optional[str] = None
    discount_amount: Optional[int] = 0
    event_date: Optional[date] = None
