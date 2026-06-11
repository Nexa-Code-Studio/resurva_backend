import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.summaries.models import DailySummary, MonthlySummary
from app.modules.summaries.repository import DailySummaryRepository, MonthlySummaryRepository


class SummaryService:
    def __init__(self, db: AsyncSession):
        self.daily_repo = DailySummaryRepository(db)
        self.monthly_repo = MonthlySummaryRepository(db)

    async def get_daily_summary(self, store_id: uuid.UUID, summary_date: date) -> DailySummary | None:
        result = await self.daily_repo.db.execute(
            select(DailySummary).filter(
                DailySummary.store_id == store_id,
                DailySummary.summary_date == summary_date
            )
        )
        return result.scalar_one_or_none()

    async def get_monthly_summaries(self, store_id: uuid.UUID, year: int) -> Sequence[MonthlySummary]:
        result = await self.monthly_repo.db.execute(
            select(MonthlySummary).filter(
                MonthlySummary.store_id == store_id,
                MonthlySummary.year == year
            )
        )
        return result.scalars().all()

    async def list_daily_summaries_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[DailySummary], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.daily_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def list_monthly_summaries_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[MonthlySummary], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.monthly_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

