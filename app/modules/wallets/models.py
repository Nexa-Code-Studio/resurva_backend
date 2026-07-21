import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, JSON, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import WalletTransactionType, WalletType, WalletTransactionCategory, TransactionStatus
from app.db.base import Base, CreatedAtMixin, IdMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from app.modules.business.models import Business
    from app.modules.stores.models import Store
    from app.modules.transactions.models import Transaction


class Wallet(Base, IdMixin, UpdatedAtMixin):
    __tablename__ = "wallets"

    store_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=True
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=True
    )
    type: Mapped[WalletType] = mapped_column(
        SQLEnum(WalletType),
        default=WalletType.DIGITAL,
        nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saved_bank_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Unique constraint on (store_id, type) and (business_id, type)
    __table_args__ = (
        UniqueConstraint("store_id", "type", name="uq_store_wallet_type"),
        UniqueConstraint("business_id", "type", name="uq_business_wallet_type"),
    )

    # Relationships
    store: Mapped[Optional["Store"]] = relationship("Store", back_populates="wallets")
    business: Mapped[Optional["Business"]] = relationship("Business", back_populates="wallets")
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")



class WalletTransaction(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        Index("idx_wtx_wallet_date", "wallet_id", "transaction_date"),
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True
    )
    withdrawal_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("withdrawal_requests.id", ondelete="SET NULL"),
        nullable=True
    )
    type: Mapped[WalletTransactionType] = mapped_column(SQLEnum(WalletTransactionType), nullable=False)
    category: Mapped[WalletTransactionCategory] = mapped_column(SQLEnum(WalletTransactionCategory), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="wallet_transactions")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="wallet_transactions")
    withdrawal_request: Mapped[Optional["WithdrawalRequest"]] = relationship("WithdrawalRequest", back_populates="wallet_transactions")

    @property
    def wallet_type(self) -> WalletType:
        return self.wallet.type

    @property
    def payment_details(self) -> dict | None:
        return self.transaction.payment_details if self.transaction else None


class WithdrawalRequest(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "withdrawal_requests"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    bank_name: Mapped[str] = mapped_column(String, nullable=False)
    account_number: Mapped[str] = mapped_column(String, nullable=False)
    account_holder: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store")
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship("WalletTransaction", back_populates="withdrawal_request")
