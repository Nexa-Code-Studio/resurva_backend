import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderChannel, OrderStatus
from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.carbon.models import CarbonLog
    from app.modules.discounts.models import Discount
    from app.modules.products.models import Product
    from app.modules.stores.models import Store
    from app.modules.transactions.models import Transaction
    from app.modules.users.models import User
    from app.modules.inventory.models import InventoryBatch


class Order(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "orders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_discount: Mapped[int] = mapped_column(Integer, nullable=False)
    final_price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    channel: Mapped[OrderChannel] = mapped_column(SQLEnum(OrderChannel), default=OrderChannel.MARKETPLACE, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    store: Mapped["Store"] = relationship("Store", back_populates="orders")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    order_discounts: Mapped[list["OrderDiscount"]] = relationship("OrderDiscount", back_populates="order", cascade="all, delete-orphan")
    carbon_logs: Mapped[list["CarbonLog"]] = relationship("CarbonLog", back_populates="order", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base, IdMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
    order_item_batches: Mapped[list["OrderItemBatch"]] = relationship("OrderItemBatch", back_populates="order_item", cascade="all, delete-orphan")


class OrderDiscount(Base, IdMixin):
    __tablename__ = "order_discounts"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    discount_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"),
        nullable=False
    )
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_discounts")
    discount: Mapped["Discount"] = relationship("Discount", back_populates="order_discounts")


class OrderItemBatch(Base, IdMixin):
    __tablename__ = "order_item_batches"

    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False
    )
    inventory_batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_batches.id", ondelete="RESTRICT"),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    order_item: Mapped["OrderItem"] = relationship("OrderItem", back_populates="order_item_batches")
    inventory_batch: Mapped["InventoryBatch"] = relationship("InventoryBatch", back_populates="order_item_batches")
