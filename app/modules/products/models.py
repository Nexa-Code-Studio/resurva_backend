import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ExpiryAlertStatus, ProductType
from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.orders.models import OrderItem
    from app.modules.reviews.models import Review
    from app.modules.stores.models import Store
    from app.modules.inventory.models import ExpiryAlert, InventoryBatch


class Product(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "products"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    original_price: Mapped[int] = mapped_column(Integer, nullable=False)
    discounted_price: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    product_type: Mapped[ProductType] = mapped_column(SQLEnum(ProductType), nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="products")
    product_ingredients: Mapped[list["ProductIngredient"]] = relationship("ProductIngredient", back_populates="product", cascade="all, delete-orphan")
    inventory_batches: Mapped[list["InventoryBatch"]] = relationship("InventoryBatch", back_populates="product", cascade="all, delete-orphan")
    expiry_alerts: Mapped[list["ExpiryAlert"]] = relationship("ExpiryAlert", back_populates="product", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")


class Ingredient(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "ingredients"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String, nullable=False)  # "gram", "ml", "pcs"
    carbon_per_unit: Mapped[float] = mapped_column(Float, nullable=False)  # kg CO2e per unit

    # Relationships
    product_ingredients: Mapped[list["ProductIngredient"]] = relationship("ProductIngredient", back_populates="ingredient", cascade="all, delete-orphan")


class ProductIngredient(Base, IdMixin):
    __tablename__ = "product_ingredients"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="product_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="product_ingredients")


