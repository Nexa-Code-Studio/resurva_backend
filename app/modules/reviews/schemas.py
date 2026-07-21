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
    attachments: list[str] | None = None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID | None
    user_id: uuid.UUID
    description: str
    rating: int
    label: str | None
    is_image: bool
    attachments: list[str] | None = None
    created_at: datetime
    
    # Joined/Property fields
    customer_name: str | None = None
    customer_avatar: str | None = None
    product_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewsSummaryResponse(BaseModel):
    summary: str
    avg_rating: float
    total_reviews: int
