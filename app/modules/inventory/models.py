import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ExpiryAlertStatus
from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.products.models import Product
    from app.modules.stores.models import Store
    from app.modules.orders.models import OrderItemBatch


class InventoryBatch(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "inventory_batches"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_batches")
    store: Mapped["Store"] = relationship("Store", back_populates="inventory_batches")
    order_item_batches: Mapped[list["OrderItemBatch"]] = relationship("OrderItemBatch", back_populates="inventory_batch")


class ExpiryAlert(Base, IdMixin):
    __tablename__ = "expiry_alerts"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    days_until_expiry: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ExpiryAlertStatus] = mapped_column(SQLEnum(ExpiryAlertStatus), nullable=False)
    alerted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="expiry_alerts")
    store: Mapped["Store"] = relationship("Store", back_populates="expiry_alerts")
