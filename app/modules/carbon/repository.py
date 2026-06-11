from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.carbon.models import CarbonLog


class CarbonRepository(BaseRepository[CarbonLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(CarbonLog, db)
