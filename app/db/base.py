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


# Import all models here for Alembic detection
# (They will be populated below as we create them)
