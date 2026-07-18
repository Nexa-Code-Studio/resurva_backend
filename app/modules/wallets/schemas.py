import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import WalletTransactionType, WalletType, WalletTransactionCategory, TransactionStatus


class WalletResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    type: WalletType
    balance: int
    saved_bank_info: dict | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletTransactionResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    wallet_type: WalletType
    transaction_id: uuid.UUID | None = None
    withdrawal_request_id: uuid.UUID | None = None
    type: WalletTransactionType
    category: WalletTransactionCategory
    amount: int
    balance_after: int
    note: str | None = None
    payment_details: dict | None = None
    transaction_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletTransactionCreate(BaseModel):
    wallet_type: WalletType
    type: WalletTransactionType
    category: WalletTransactionCategory
    amount: int
    note: str | None = None
    transaction_date: datetime | None = None


class WithdrawalRequestCreate(BaseModel):
    bank_name: str
    account_number: str
    account_holder: str
    amount: int
    save_account: bool = False


class WithdrawalRequestResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    bank_name: str
    account_number: str
    account_holder: str
    amount: int
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
