import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LogCreate(BaseModel):
    platform: str
    severity: str
    event: str
    user_email: str | None = None
    ip_address: str | None = None
    details: dict | None = None


class LogResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    platform: str
    severity: str
    event: str
    user_id: uuid.UUID | None
    user_email: str | None
    ip_address: str | None
    details: dict | None = None

    model_config = ConfigDict(from_attributes=True)
