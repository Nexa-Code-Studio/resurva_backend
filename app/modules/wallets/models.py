import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import WalletTransactionType
from app.db.base import Base, CreatedAtMixin, IdMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from app.modules.stores.models import Store
    from app.modules.transactions.models import Transaction


class Wallet(Base, IdMixin, UpdatedAtMixin):
    __tablename__ = "wallets"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="wallet")
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "wallet_transactions"

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True
    )
    type: Mapped[WalletTransactionType] = mapped_column(SQLEnum(WalletTransactionType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="wallet_transactions")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="wallet_transactions")
