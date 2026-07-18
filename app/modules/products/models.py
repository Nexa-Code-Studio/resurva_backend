import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Boolean
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
    product_type: Mapped[str] = mapped_column(String, nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    expiry_time: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    sku: Mapped[str | None] = mapped_column(String, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_surplus_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    surplus_trigger_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ingredients_data: Mapped[str | None] = mapped_column(String, nullable=True)
    supplier_lead_time_days: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="products")

    @property
    def store_name(self) -> str | None:
        if "store" in self.__dict__ and self.store is not None:
            return self.store.name
        return None
    product_ingredients: Mapped[list["ProductIngredient"]] = relationship("ProductIngredient", back_populates="product", cascade="all, delete-orphan")
    inventory_batches: Mapped[list["InventoryBatch"]] = relationship("InventoryBatch", back_populates="product", cascade="all, delete-orphan")
    expiry_alerts: Mapped[list["ExpiryAlert"]] = relationship("ExpiryAlert", back_populates="product", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")
    variant_groups: Mapped[list["ProductVariantGroup"]] = relationship("ProductVariantGroup", back_populates="product", cascade="all, delete-orphan")


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


class ProductVariantGroup(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "product_variant_groups"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_selections: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variant_groups")
    options: Mapped[list["ProductVariantOption"]] = relationship("ProductVariantOption", back_populates="group", cascade="all, delete-orphan")


class ProductVariantOption(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "product_variant_options"

    variant_group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variant_groups.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    additional_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    group: Mapped["ProductVariantGroup"] = relationship("ProductVariantGroup", back_populates="options")

