import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessBase(BaseModel):
    name: str
    email: str
    phone: str | None = None


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class BusinessResponse(BusinessBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
