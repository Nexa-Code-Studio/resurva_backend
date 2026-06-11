import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    store_id: uuid.UUID
    product_id: uuid.UUID | None = None
    description: str
    rating: int = Field(..., ge=1, le=5)
    label: str | None = None
    is_image: bool = False


class ReviewResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID | None
    user_id: uuid.UUID
    description: str
    rating: int
    label: str | None
    is_image: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
