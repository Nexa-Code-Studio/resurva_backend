import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# Base Mixins
class IdMixin:
    """Mixin to add a UUID primary key to a model."""
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )


class CreatedAtMixin:
    """Mixin to add a timezone-aware created_at timestamp to a model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now()
    )


class UpdatedAtMixin:
    """Mixin to add a timezone-aware updated_at timestamp to a model."""
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC)
    )


class TimestampMixin(CreatedAtMixin, UpdatedAtMixin):
    """Mixin to add both created_at and updated_at timestamps to a model."""
    pass


def import_all_models():
    """Import all model modules to populate Base.metadata for table creation and migrations."""
    from app.modules.users.models import User  # noqa: F401
    from app.modules.business.models import Business  # noqa: F401
    from app.modules.stores.models import Store  # noqa: F401
    from app.modules.products.models import Product  # noqa: F401
    from app.modules.inventory.models import InventoryBatch, InventoryTransaction, ExpiryAlert  # noqa: F401
    from app.modules.orders.models import Order, OrderItem, OrderDiscount, OrderItemBatch, OrderItemVariantOption, OrderEscrow  # noqa: F401
    from app.modules.discounts.models import Discount  # noqa: F401
    from app.modules.wallets.models import Wallet, WalletTransaction  # noqa: F401
    from app.modules.reviews.models import Review  # noqa: F401
    from app.modules.carbon.models import CarbonLog  # noqa: F401
    from app.modules.summaries.models import DailySummary, MonthlySummary  # noqa: F401
    from app.modules.verifications.models import PartnerVerification  # noqa: F401
    from app.modules.cart.models import CartReservation  # noqa: F401
    from app.modules.logs.models import LogSystem  # noqa: F401
