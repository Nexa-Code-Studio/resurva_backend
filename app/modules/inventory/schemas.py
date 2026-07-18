import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import ExpiryAlertStatus


class InventoryBatchCreate(BaseModel):
    product_id: uuid.UUID
    store_id: uuid.UUID
    quantity: int
    remaining_quantity: int
    expired_at: datetime
    surplus_starts_at: datetime | None = None


class InventoryBatchUpdate(BaseModel):
    quantity: int | None = None
    remaining_quantity: int | None = None
    expired_at: datetime | None = None
    surplus_starts_at: datetime | None = None


class InventoryBatchResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    quantity: int
    remaining_quantity: int
    expired_at: datetime
    surplus_starts_at: datetime | None = None
    batch_tag: str | None = None
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


class InventoryTransactionResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    inventory_batch_id: uuid.UUID | None = None
    batch_tag: str | None = None
    type: str
    quantity: int
    reason: str
    reference: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
