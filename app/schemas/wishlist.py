import uuid
from datetime import datetime
from pydantic import BaseModel


class WishlistItemAdd(BaseModel):
    product_id: uuid.UUID


class WishlistItemResponse(BaseModel):
    id: int
    product_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
