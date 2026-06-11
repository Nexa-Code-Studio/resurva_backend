import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.repository import ExpiryAlertRepository, InventoryBatchRepository
from app.modules.inventory.models import ExpiryAlert, InventoryBatch


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.batch_repo = InventoryBatchRepository(db)
        self.alert_repo = ExpiryAlertRepository(db)

    async def get_store_batches(self, store_id: uuid.UUID) -> Sequence[InventoryBatch]:
        result = await self.batch_repo.db.execute(
            select(InventoryBatch).filter(InventoryBatch.store_id == store_id)
        )
        return result.scalars().all()

    async def get_store_expiry_alerts(self, store_id: uuid.UUID) -> Sequence[ExpiryAlert]:
        result = await self.alert_repo.db.execute(
            select(ExpiryAlert).filter(ExpiryAlert.store_id == store_id)
        )
        return result.scalars().all()

    async def list_batches_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[InventoryBatch], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.batch_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def list_alerts_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[ExpiryAlert], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.alert_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

