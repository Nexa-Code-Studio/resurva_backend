import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.core.enums import UserRole


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    business_id: uuid.UUID | None = None
    store_id: uuid.UUID | None = None
    full_name: str | None = None
    phone_number: str | None = None
    photo_url: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    business_id: uuid.UUID | None = None
    full_name: str | None = None
    phone_number: str | None = None
    photo_url: str | None = None


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("photo_url", mode="before")
    @classmethod
    def resolve_photo_url(cls, v: str | None) -> str | None:
        if not v:
            return v
        if v.startswith("http://") or v.startswith("https://"):
            return v
        from app.storage.factory import StorageFactory
        storage = StorageFactory.get_storage_provider()
        return storage.get_file_url(v)

    @model_validator(mode="after")
    def populate_default_fullname(self) -> "UserResponse":
        if not self.full_name:
            self.full_name = self.username
        return self
