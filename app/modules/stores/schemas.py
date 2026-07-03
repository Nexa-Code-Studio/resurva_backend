import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    name: str = Field(..., description="Name of the store")
    address: str = Field(..., description="Full address")
    city: str = Field(..., description="City location")
    longitude: float = Field(..., description="GPS Longitude coordinate")
    latitude: float = Field(..., description="GPS Latitude coordinate")
    business_id: uuid.UUID = Field(..., description="Parent Business entity UUID")
    is_active: bool = True
    category: str | None = Field(None, description="Store category")
    pickup_time: str | None = Field(None, description="Store pickup window hours")


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    is_active: bool | None = None
    category: str | None = None
    pickup_time: str | None = None


class StoreResponse(StoreBase):
    id: uuid.UUID
    rating: float
    created_at: datetime
    active_surplus: int = 0
    total_reviews: int = 0
    eco_impact_saved_meals: int = 0
    eco_impact_co2: float = 0.0

    model_config = ConfigDict(from_attributes=True)
