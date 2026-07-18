import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from app.core.enums import ProductType


class ProductVariantOptionBase(BaseModel):
    name: str
    additional_price: int = 0


class ProductVariantOptionCreate(ProductVariantOptionBase):
    pass


class ProductVariantOptionUpdate(BaseModel):
    name: str | None = None
    additional_price: int | None = None


class ProductVariantOptionResponse(ProductVariantOptionBase):
    id: uuid.UUID
    variant_group_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ProductVariantGroupBase(BaseModel):
    name: str
    is_required: bool = False
    max_selections: int = 1


class ProductVariantGroupCreate(ProductVariantGroupBase):
    options: list[ProductVariantOptionCreate] = []


class ProductVariantGroupUpdate(BaseModel):
    name: str | None = None
    is_required: bool | None = None
    max_selections: int | None = None


class ProductVariantGroupResponse(ProductVariantGroupBase):
    id: uuid.UUID
    product_id: uuid.UUID
    options: list[ProductVariantOptionResponse] = []

    model_config = ConfigDict(from_attributes=True)


import json

class ProductBase(BaseModel):
    name: str = Field(..., description="Name of the food product")
    description: str | None = Field(None, description="Detailed description")
    original_price: int = Field(..., description="Original price in IDR")
    discounted_price: int = Field(..., description="Discounted price in IDR")
    stock: int = Field(..., description="Quantity in stock")
    product_type: str = Field(..., description="Product category")
    expired_at: datetime = Field(..., description="Expiration timestamp")
    store_id: uuid.UUID = Field(..., description="Parent Store UUID")
    image_url: str | None = Field(None, description="Product image URL")
    expiry_time: int = Field(24, description="Default expiry time in hours")
    sku: str | None = Field(None, description="Stock Keeping Unit code")
    weight: float = Field(0.1, description="Weight in kg")
    is_published: bool = Field(True, description="Visible on marketplace")
    auto_surplus_enabled: bool = Field(False, description="Auto-convert to surplus mode")
    surplus_trigger_hours: int = Field(0, description="Hours before expiry to auto-activate surplus")
    supplier_lead_time_days: int = Field(2, description="Supplier lead time in days")


class ProductCreate(ProductBase):
    variant_groups: list[ProductVariantGroupCreate] = []
    ingredients: list[dict] = []


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    original_price: int | None = None
    discounted_price: int | None = None
    stock: int | None = None
    product_type: str | None = None
    expired_at: datetime | None = None
    store_id: uuid.UUID | None = None
    image_url: str | None = None
    expiry_time: int | None = None
    sku: str | None = None
    weight: float | None = None
    is_published: bool | None = None
    auto_surplus_enabled: bool | None = None
    surplus_trigger_hours: int | None = None
    supplier_lead_time_days: int | None = None
    variant_groups: list[ProductVariantGroupCreate] | None = None
    ingredients: list[dict] | None = None


class ProductResponse(ProductBase):
    id: uuid.UUID
    sold: int
    created_at: datetime
    store_name: str | None = None
    variant_groups: list[ProductVariantGroupResponse] = []
    ingredients: list[dict] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def load_ingredients(cls, data: any) -> any:
        if hasattr(data, "ingredients_data") and data.ingredients_data:
            try:
                # Eagerly assign to the object so from_attributes picks it up
                data.ingredients = json.loads(data.ingredients_data)
            except Exception:
                data.ingredients = []
        elif isinstance(data, dict) and data.get("ingredients_data"):
            try:
                data["ingredients"] = json.loads(data["ingredients_data"])
            except Exception:
                data["ingredients"] = []
        return data

    @field_validator("image_url", mode="before")
    @classmethod
    def resolve_image_url(cls, v: str | None) -> str | None:
        if not v:
            return v
        # If it's already an absolute URL (e.g. external asset), return as is
        if v.startswith("http://") or v.startswith("https://"):
            return v
        from app.storage.factory import StorageFactory
        storage = StorageFactory.get_storage_provider()
        return storage.get_file_url(v)

