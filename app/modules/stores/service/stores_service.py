import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stores.models import Store
from app.modules.stores.repository import StoreRepository
from app.modules.stores.schemas import StoreCreate, StoreUpdate
from app.modules.wallets.models import Wallet


class StoreService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = StoreRepository(db)

    async def get_store(self, store_id: uuid.UUID) -> Store | None:
        return await self.repository.get_by_id(store_id)

    async def list_stores(self, skip: int = 0, limit: int = 100) -> Sequence[Store]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def list_stores_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        business_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Store], int]:
        filters = {}
        if business_id is not None:
            filters["business_id"] = business_id
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )


    async def create_store(self, schema: StoreCreate) -> Store:
        # Create store
        store_data = schema.model_dump()
        store = await self.repository.create(store_data)

        # Initialize Wallet for the Store
        # Note: According to the architecture rules, services must use repositories.
        # So we add the wallet to session here.
        wallet = Wallet(store_id=store.id, balance=0)
        self.db.add(wallet)
        await self.db.flush()

        return store

    async def update_store(self, store_id: uuid.UUID, schema: StoreUpdate) -> Store:
        store = await self.repository.get_by_id(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
        store_data = schema.model_dump(exclude_unset=True)
        return await self.repository.update(store, store_data)

    async def delete_store(self, store_id: uuid.UUID) -> bool:
        return await self.repository.delete(store_id)
