import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    operating_hours: str | None = Field(None, description="Daily store operating hours")
    image_url: str | None = Field(None, description="Publicly accessible logo or cover image URL")
    categories_data: str | None = Field(None, description="Serialized store custom categories")
    description: str | None = Field(None, description="Detailed description of the store")
    banner_url: str | None = Field(None, description="Publicly accessible banner image URL")
    is_branch: bool = False


class StoreCreate(StoreBase):
    username: str | None = Field(None, description="Username for store seller login")
    password: str | None = Field(None, description="Password for store seller login")
    email: str | None = Field(None, description="Email address for store/seller")
    contact: str | None = Field(None, description="Contact phone number")


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    is_active: bool | None = None
    category: str | None = None
    pickup_time: str | None = None
    operating_hours: str | None = None
    image_url: str | None = None
    categories_data: str | None = None
    description: str | None = None
    banner_url: str | None = None
    is_branch: bool | None = None
    business_id: uuid.UUID | None = None


class ResetPasswordSchema(BaseModel):
    new_password: str = Field(..., min_length=6, description="New password for store seller")


class BusinessInfo(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str | None = None


class StoreResponse(StoreBase):
    id: uuid.UUID
    rating: float
    created_at: datetime
    active_surplus: int = 0
    total_reviews: int = 0
    eco_impact_saved_meals: int = 0
    eco_impact_co2: float = 0.0
    monthly_revenue: int = 0
    email: str | None = None
    contact: str | None = None
    business: BusinessInfo | None = None


    model_config = ConfigDict(from_attributes=True)

    @field_validator("image_url", "banner_url", mode="before")
    @classmethod
    def resolve_image_url(cls, v: str | None) -> str | None:
        if not v:
            return v
        if v.startswith("http://") or v.startswith("https://"):
            return v
        from app.storage.factory import StorageFactory
        storage = StorageFactory.get_storage_provider()
        return storage.get_file_url(v)

    @field_validator("pickup_time", mode="before")
    @classmethod
    def resolve_pickup_time(cls, v: str | None) -> str | None:
        return v or "19:30 - 21:00 WIB"


class EnterpriseRequestBase(BaseModel):
    corporate_name: str
    pic_name: str
    email: str
    phone: str


class EnterpriseRequestCreate(EnterpriseRequestBase):
    pass


class EnterpriseRequestResponse(EnterpriseRequestBase):
    id: uuid.UUID
    store_id: uuid.UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


