import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ProductType


class ProductBase(BaseModel):
    name: str = Field(..., description="Name of the food product")
    description: str | None = Field(None, description="Detailed description")
    original_price: int = Field(..., description="Original price in IDR")
    discounted_price: int = Field(..., description="Discounted price in IDR")
    stock: int = Field(..., description="Quantity in stock")
    product_type: ProductType = Field(..., description="Product category")
    expired_at: datetime = Field(..., description="Expiration timestamp")
    store_id: uuid.UUID = Field(..., description="Parent Store UUID")
    image_url: str | None = Field(None, description="Product image URL")
    expiry_time: int = Field(24, description="Default expiry time in hours")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    original_price: int | None = None
    discounted_price: int | None = None
    stock: int | None = None
    product_type: ProductType | None = None
    expired_at: datetime | None = None
    store_id: uuid.UUID | None = None
    image_url: str | None = None
    expiry_time: int | None = None


class ProductResponse(ProductBase):
    id: uuid.UUID
    sold: int
    created_at: datetime
    store_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
