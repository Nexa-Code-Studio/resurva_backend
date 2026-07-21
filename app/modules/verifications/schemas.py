import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PartnerVerificationBase(BaseModel):
    partner_type: str  # "MERCHANT" or "ENTERPRISE"
    name: str
    owner_or_director: str
    category: str | None = None
    branch_count: int | None = None
    address: str
    email: str | None = None
    phone: str | None = None
    documents: list[str] | None = None


class PartnerVerificationCreate(PartnerVerificationBase):
    pass


class PartnerVerificationStatusUpdate(BaseModel):
    status: str  # "APPROVED" or "REJECTED"
    rejection_reason: str | None = None


class PartnerVerificationResponse(PartnerVerificationBase):
    id: uuid.UUID
    status: str
    rejection_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
