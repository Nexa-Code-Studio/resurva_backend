import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderChannel, OrderStatus
from app.db.base import Base, CreatedAtMixin, IdMixin, UpdatedAtMixin

if TYPE_CHECKING:
    from app.modules.carbon.models import CarbonLog
    from app.modules.discounts.models import Discount
    from app.modules.products.models import Product
    from app.modules.stores.models import Store
    from app.modules.transactions.models import Transaction
    from app.modules.users.models import User
    from app.modules.inventory.models import InventoryBatch
    from app.modules.products.models import ProductVariantOption
    from app.modules.reviews.models import Review


class Order(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_order_store_status_created", "store_id", "status", "created_at"),
    )

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
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_code: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    store: Mapped["Store"] = relationship("Store", back_populates="orders")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    order_discounts: Mapped[list["OrderDiscount"]] = relationship("OrderDiscount", back_populates="order", cascade="all, delete-orphan")
    carbon_logs: Mapped[list["CarbonLog"]] = relationship("CarbonLog", back_populates="order", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="order", cascade="all, delete-orphan")
    review: Mapped[Optional["Review"]] = relationship("Review", back_populates="order", uselist=False, cascade="all, delete-orphan")

    @property
    def store_name(self) -> str:
        return self.store.name if self.store else "Toko RESURVA"

    @property
    def store_latitude(self) -> float | None:
        return self.store.latitude if self.store else None

    @property
    def store_longitude(self) -> float | None:
        return self.store.longitude if self.store else None

    @property
    def store_address(self) -> str:
        return self.store.address if self.store else "Jl. Semeru No. 45, Malang"

    @property
    def applied_voucher_code(self) -> str | None:
        if self.order_discounts:
            od = self.order_discounts[0]
            if od.discount:
                return od.discount.code
        return None

    @property
    def applied_voucher_name(self) -> str | None:
        if self.order_discounts:
            od = self.order_discounts[0]
            if od.discount:
                return od.discount.name
        return None

    @property
    def voucher_discount(self) -> int:
        if self.order_discounts:
            return sum(od.discount_amount for od in self.order_discounts)
        return 0

    @property
    def store_image_url(self) -> str | None:
        if self.store and self.store.image_url:
            from app.storage.factory import StorageFactory
            storage = StorageFactory.get_storage_provider()
            return storage.get_file_url(self.store.image_url)
        return None

    @property
    def customer_name(self) -> str:
        return self.user.username if self.user else "Customer"

    @property
    def payment_method(self) -> str:
        for tx in self.transactions:
            if tx.status.value == "success":
                return tx.payment_method.value
        if self.transactions:
            return self.transactions[0].payment_method.value
        return "Tunai"

    @property
    def order_type(self) -> str:
        if self.channel.value == "kasir":
            return "POS Dine-In"
        return "Online Pickup"


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
    order_item_variant_options: Mapped[list["OrderItemVariantOption"]] = relationship("OrderItemVariantOption", back_populates="order_item", cascade="all, delete-orphan")

    @property
    def product_name(self) -> str:
        return self.product.name if self.product else "Unknown Product"

    @property
    def options(self) -> list[str]:
        return [opt.name for opt in self.order_item_variant_options] if self.order_item_variant_options else []


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


class OrderItemVariantOption(Base, IdMixin):
    __tablename__ = "order_item_variant_options"

    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False
    )
    variant_option_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variant_options.id", ondelete="SET NULL"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    additional_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    order_item: Mapped["OrderItem"] = relationship("OrderItem", back_populates="order_item_variant_options")
    variant_option: Mapped["ProductVariantOption | None"] = relationship("ProductVariantOption")


class OrderEscrow(Base, IdMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "order_escrows"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="held", nullable=False)  # held, released, refunded
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    store: Mapped["Store"] = relationship("Store")
