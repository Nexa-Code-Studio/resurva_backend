from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.inventory.models import ExpiryAlert, InventoryBatch


class InventoryBatchRepository(BaseRepository[InventoryBatch]):
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryBatch, db)


class ExpiryAlertRepository(BaseRepository[ExpiryAlert]):
    def __init__(self, db: AsyncSession):
        super().__init__(ExpiryAlert, db)
