from typing import Any
from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin


class PartnerVerification(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "partner_verifications"

    partner_type: Mapped[str] = mapped_column(String, nullable=False)  # "MERCHANT" or "ENTERPRISE"
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_or_director: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)  # F&B, Cafe, Cafe / Coffee Shop, etc. (for Merchant)
    branch_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # (for Enterprise)
    address: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    documents: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # list of URLs or paths
    status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False)  # "PENDING", "APPROVED", "REJECTED"
    rejection_reason: Mapped[str | None] = mapped_column(String, nullable=True)
