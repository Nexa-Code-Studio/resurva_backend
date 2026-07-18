import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.business.models import Business
    from app.modules.discounts.models import Discount
    from app.modules.orders.models import Order
    from app.modules.inventory.models import ExpiryAlert, InventoryBatch
    from app.modules.products.models import Product
    from app.modules.reviews.models import Review
    from app.modules.summaries.models import DailySummary, MonthlySummary
    from app.modules.transactions.models import Transaction
    from app.modules.wallets.models import Wallet


class StoreCategory(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "store_categories"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class Store(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "stores"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("store_categories.id", ondelete="SET NULL"),
        nullable=True
    )
    pickup_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    categories_data: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_branch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @property
    def category(self) -> Optional[str]:
        return self.store_category.name if self.store_category else None

    # Relationships
    store_category: Mapped[Optional["StoreCategory"]] = relationship("StoreCategory")
    business: Mapped["Business"] = relationship("Business", back_populates="stores")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    inventory_batches: Mapped[list["InventoryBatch"]] = relationship("InventoryBatch", back_populates="store", cascade="all, delete-orphan")
    expiry_alerts: Mapped[list["ExpiryAlert"]] = relationship("ExpiryAlert", back_populates="store", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="store", cascade="all, delete-orphan")
    discounts: Mapped[list["Discount"]] = relationship("Discount", back_populates="store", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="store", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="store", cascade="all, delete-orphan")
    wallets: Mapped[list["Wallet"]] = relationship("Wallet", back_populates="store", cascade="all, delete-orphan")
    daily_summaries: Mapped[list["DailySummary"]] = relationship("DailySummary", back_populates="store", cascade="all, delete-orphan")
    monthly_summaries: Mapped[list["MonthlySummary"]] = relationship("MonthlySummary", back_populates="store", cascade="all, delete-orphan")


class EnterpriseRequest(Base, IdMixin, TimestampMixin):
    __tablename__ = "enterprise_requests"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    corporate_name: Mapped[str] = mapped_column(String, nullable=False)
    pic_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store")

