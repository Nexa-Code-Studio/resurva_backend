import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessBase(BaseModel):
    name: str
    email: str
    phone: str | None = None
    address: str | None = None
    legal_entity: str | None = None
    pic: str | None = None
    sdg_commitment: str | None = None
    year_founded: str | None = None
    logo_url: str | None = None
    description: str | None = None
    website: str | None = None


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    legal_entity: str | None = None
    pic: str | None = None
    sdg_commitment: str | None = None
    year_founded: str | None = None
    logo_url: str | None = None
    description: str | None = None
    website: str | None = None


class BusinessResponse(BusinessBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

