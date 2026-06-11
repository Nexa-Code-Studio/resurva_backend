import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import ExpiryAlertStatus


class InventoryBatchResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    quantity: int
    remaining_quantity: int
    expired_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpiryAlertResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    days_until_expiry: int
    status: ExpiryAlertStatus
    alerted_at: datetime

    model_config = ConfigDict(from_attributes=True)
