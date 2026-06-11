from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.stores.models import Store


class StoreRepository(BaseRepository[Store]):
    def __init__(self, db: AsyncSession):
        super().__init__(Store, db)
