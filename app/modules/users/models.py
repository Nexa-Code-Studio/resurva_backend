import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum, Boolean, Float
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.business.models import Business
    from app.modules.carbon.models import CarbonLog
    from app.modules.orders.models import Order
    from app.modules.reviews.models import Review
    from app.modules.stores.models import Store


class User(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "users"

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True
    )
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    default_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    business: Mapped[Optional["Business"]] = relationship("Business", back_populates="users")
    store: Mapped[Optional["Store"]] = relationship("Store")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    carbon_logs: Mapped[list["CarbonLog"]] = relationship("CarbonLog", back_populates="user", cascade="all, delete-orphan")
