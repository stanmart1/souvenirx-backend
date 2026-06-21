from __future__ import annotations

from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class ProductImageIn(BaseModel):
    url: str
    alt_text: str = ""
    sort_order: int = 0


class ProductTierIn(BaseModel):
    min_qty: int = Field(ge=1)
    unit_price: int = Field(ge=0)


class ProductCustomizationIn(BaseModel):
    type: str = Field(pattern="^(text|option|logo)$")
    label: str
    max_length: Optional[int] = None
    values: Optional[list[str]] = None


class ProductVariantIn(BaseModel):
    sku: str
    attributes: dict[str, str]  # e.g., {"color": "red", "size": "M"}
    price: int = Field(ge=0)
    moq: int = Field(ge=1)
    stock: int = 0


class ProductCreate(BaseModel):
    slug: str
    name: str
    category: str
    description: str
    base_price: int = Field(ge=0)
    moq: int = Field(ge=1)
    stock: int = 0
    tags: list[str] = []
    images: list[str] = []
    tiers: list[ProductTierIn] = []
    customizations: list[ProductCustomizationIn] = []
    variants: list[ProductVariantIn] = []
    is_group_parent: bool = False
    product_group_id: Optional[int] = None
    customization_options: Optional[dict] = None
    # Example: {
    #   "colors": [{"name": "Gold", "hex": "#D4AF37"}, ...],
    #   "allow_text": true,
    #   "allow_icon": true,
    #   "allow_image": true,
    #   "allowed_fonts": ["Inter", "Dancing Script"],
    #   "default_text": "Your text"
    # }


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[int] = Field(default=None, ge=0)
    moq: Optional[int] = Field(default=None, ge=1)
    stock: Optional[int] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None
    variants: Optional[list[ProductVariantIn]] = None
    is_group_parent: Optional[bool] = None
    product_group_id: Optional[int] = None
    customization_options: Optional[dict] = None


class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    icon: str


class ProductListResponse(BaseModel):
    products: list[dict]
    total: int
    page: int
    pages: int


class ReviewCreate(BaseModel):
    author: str = "Anonymous"
    rating: int = Field(ge=1, le=5)
    title: str
    text: str
