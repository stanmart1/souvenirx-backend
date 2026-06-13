from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AdCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    image_url: str = Field(..., max_length=500)
    mobile_image_url: Optional[str] = Field(None, max_length=500)
    link_url: Optional[str] = Field(None, max_length=500)
    position: str = Field(..., pattern="^(hero|sidebar|banner|footer)$")
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sort_order: int = 0


class AdUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    mobile_image_url: Optional[str] = Field(None, max_length=500)
    link_url: Optional[str] = Field(None, max_length=500)
    position: Optional[str] = Field(None, pattern="^(hero|sidebar|banner|footer)$")
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sort_order: Optional[int] = None
