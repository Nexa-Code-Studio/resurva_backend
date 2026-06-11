from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.summaries.models import DailySummary, MonthlySummary


class DailySummaryRepository(BaseRepository[DailySummary]):
    def __init__(self, db: AsyncSession):
        super().__init__(DailySummary, db)


class MonthlySummaryRepository(BaseRepository[MonthlySummary]):
    def __init__(self, db: AsyncSession):
        super().__init__(MonthlySummary, db)
