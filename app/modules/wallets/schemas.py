import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import WalletTransactionType


class WalletResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    balance: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletTransactionResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    transaction_id: uuid.UUID | None
    type: WalletTransactionType
    amount: int
    balance_after: int
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
