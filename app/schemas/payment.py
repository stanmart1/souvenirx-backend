from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class PaymentInitialize(BaseModel):
    order_number: str


class PromoValidate(BaseModel):
    code: str
    subtotal: int = Field(ge=0)


class OrderStatusUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None


class BankTransferVerify(BaseModel):
    approved: bool


class AffiliatePayoutRequest(BaseModel):
    amount: Optional[int] = None


class DeliveryZoneCreate(BaseModel):
    zone_name: str
    countries: list[str] = ["Nigeria"]
    states: list[str] = []
    lgas: list[str] = []
    zone_type: str = "state"
    standard_fee: int
    express_fee: int
    eta_text: str
    is_active: bool = True
    free_shipping_threshold: int = 0
    weight_fee_per_kg: int = 0
    volume_fee_per_unit: int = 0
    min_days: int = 3
    max_days: int = 7
    is_international: bool = False
    customs_handling_fee: int = 0
    border_crossing_fee: int = 0
    default_carrier: Optional[str] = None
    auto_assign: bool = True


class DeliveryZoneUpdate(BaseModel):
    standard_fee: Optional[int] = None
    express_fee: Optional[int] = None
    eta_text: Optional[str] = None
    is_active: Optional[bool] = None
    countries: Optional[list[str]] = None
    states: Optional[list[str]] = None
    lgas: Optional[list[str]] = None
    zone_type: Optional[str] = None
    free_shipping_threshold: Optional[int] = None
    weight_fee_per_kg: Optional[int] = None
    volume_fee_per_unit: Optional[int] = None
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    is_international: Optional[bool] = None
    customs_handling_fee: Optional[int] = None
    border_crossing_fee: Optional[int] = None
    default_carrier: Optional[str] = None
    auto_assign: Optional[bool] = None


class BankAccountCreate(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    is_active: bool = True
    sort_order: int = 0


class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PromoCreate(BaseModel):
    code: str
    discount_percent: int = Field(ge=0, le=100)
    min_order_amount: int = 0
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    is_active: bool = True


class PromoUpdate(BaseModel):
    code: Optional[str] = None
    discount_percent: Optional[int] = Field(default=None, ge=0, le=100)
    min_order_amount: Optional[int] = None
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None


class AffiliateUpdate(BaseModel):
    status: Optional[str] = None
    commission_rate: Optional[float] = None
