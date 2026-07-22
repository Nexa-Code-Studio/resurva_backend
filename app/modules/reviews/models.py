import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.products.models import Product
    from app.modules.stores.models import Store
    from app.modules.users.models import User
    from app.modules.orders.models import Order


class Review(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "reviews"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    label: Mapped[str | None] = mapped_column(String, nullable=True)  # Comma-separated or JSON list
    is_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="reviews")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="review")

    @property
    def product_name(self) -> Optional[str]:
        return self.product.name if self.product else None

    @property
    def user_name(self) -> Optional[str]:
        return self.user.username if self.user else None
