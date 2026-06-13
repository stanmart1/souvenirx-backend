from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class EmailTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    subject: str = Field(..., max_length=200)
    html_content: str = Field(..., min_length=1)
    variables: Optional[dict] = None
    is_active: bool = True


class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=200)
    html_content: Optional[str] = None
    variables: Optional[dict] = None
    is_active: Optional[bool] = None
