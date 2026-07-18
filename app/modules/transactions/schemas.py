import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import PaymentMethod, TransactionStatus


class TransactionCreate(BaseModel):
    order_id: uuid.UUID
    store_id: uuid.UUID
    gross_amount: int
    platform_fee: int
    net_amount: int
    payment_method: PaymentMethod
    status: TransactionStatus = TransactionStatus.PENDING
    payment_details: dict | None = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    store_id: uuid.UUID
    gross_amount: int
    platform_fee: int
    net_amount: int
    payment_method: PaymentMethod
    status: TransactionStatus
    paid_at: datetime | None
    payment_details: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
