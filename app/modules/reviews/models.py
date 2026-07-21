import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.products.models import Product
    from app.modules.stores.models import Store
    from app.modules.users.models import User


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
    description: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    label: Mapped[str | None] = mapped_column(String, nullable=True)  # Comma-separated or JSON list
    is_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attachments: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # list of image/video URLs

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="reviews")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")

    @property
    def customer_name(self) -> str:
        if "user" in self.__dict__ and self.user is not None:
            return self.user.username
        return "Pelanggan"

    @property
    def customer_avatar(self) -> str | None:
        if "user" in self.__dict__ and self.user is not None:
            return self.user.avatar_url
        return None

    @property
    def product_name(self) -> str | None:
        if "product" in self.__dict__ and self.product is not None:
            return self.product.name
        return None
