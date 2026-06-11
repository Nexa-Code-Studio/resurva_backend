from collections.abc import Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.carbon.models import CarbonLog
from app.modules.carbon.repository import CarbonRepository


class CarbonService:
    def __init__(self, db: AsyncSession):
        self.repository = CarbonRepository(db)

    async def log_carbon_saving(self, order_id: uuid.UUID, user_id: uuid.UUID, carbon_saved: float) -> CarbonLog:
        return await self.repository.create({
            "order_id": order_id,
            "user_id": user_id,
            "carbon_saved_kg": carbon_saved
        })

    async def get_user_total_savings(self, user_id: uuid.UUID) -> float:
        result = await self.repository.db.execute(
            select(func.sum(CarbonLog.carbon_saved_kg)).filter(CarbonLog.user_id == user_id)
        )
        return result.scalar() or 0.0

    async def list_carbon_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[CarbonLog], int]:
        filters = {}
        if user_id is not None:
            filters["user_id"] = user_id
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

