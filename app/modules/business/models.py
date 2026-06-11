from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.stores.models import Store
    from app.modules.users.models import User


class Business(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="business", cascade="all, delete-orphan")
    stores: Mapped[list["Store"]] = relationship("Store", back_populates="business", cascade="all, delete-orphan")
