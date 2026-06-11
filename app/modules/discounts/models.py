import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DiscountType
from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.orders.models import OrderDiscount
    from app.modules.stores.models import Store


class Discount(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "discounts"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[DiscountType] = mapped_column(SQLEnum(DiscountType), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # Percentage or fixed value
    max_discount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_purchase: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quota: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Null = unlimited
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_voucher: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    code: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="discounts")
    order_discounts: Mapped[list["OrderDiscount"]] = relationship("OrderDiscount", back_populates="discount", cascade="all, delete-orphan")
