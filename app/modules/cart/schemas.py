import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CartReserveRequest(BaseModel):
    product_id: uuid.UUID = Field(..., description="UUID of the product to reserve")
    quantity: int = Field(..., ge=0, description="Target quantity in cart for this product (0 to release)")
    duration_seconds: int = Field(default=300, ge=30, le=3600, description="Reservation duration in seconds (default 5 min)")


class CartReserveResponse(BaseModel):
    status: str = "success"
    product_id: uuid.UUID
    reserved_quantity: int
    available_stock: int
    expires_at: datetime | None = None


class CartReleaseRequest(BaseModel):
    product_id: uuid.UUID | None = Field(default=None, description="Optional product_id to release specific item. If None, releases all user's cart reservations.")
