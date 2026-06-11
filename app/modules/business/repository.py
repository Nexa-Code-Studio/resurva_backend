from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.business.models import Business


class BusinessRepository(BaseRepository[Business]):
    def __init__(self, db: AsyncSession):
        super().__init__(Business, db)
