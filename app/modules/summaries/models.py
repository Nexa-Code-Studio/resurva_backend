import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin

if TYPE_CHECKING:
    from app.modules.stores.models import Store


class DailySummary(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "daily_summaries"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_discount_given: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    carbon_saved_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    expiry_alerts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="daily_summaries")

    __table_args__ = (
        UniqueConstraint("store_id", "summary_date", name="uq_store_summary_date"),
    )


class MonthlySummary(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "monthly_summaries"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_discount_given: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    carbon_saved_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="monthly_summaries")

    __table_args__ = (
        UniqueConstraint("store_id", "year", "month", name="uq_store_year_month"),
    )
