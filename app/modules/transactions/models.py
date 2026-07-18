import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PaymentMethod, TransactionStatus
from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.orders.models import Order
    from app.modules.stores.models import Store
    from app.modules.wallets.models import WalletTransaction


class Transaction(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "transactions"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    gross_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    net_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(SQLEnum(PaymentMethod), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="transactions")
    store: Mapped["Store"] = relationship("Store", back_populates="transactions")
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship("WalletTransaction", back_populates="transaction", cascade="all, delete-orphan")