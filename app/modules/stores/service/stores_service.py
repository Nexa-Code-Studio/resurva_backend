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

    async def _populate_store_stats(self, stores: list[Store]) -> None:
        if not stores:
            return
        
        from sqlalchemy import select, func, and_
        from datetime import datetime, UTC
        from app.modules.products.models import Product
        from app.modules.reviews.models import Review
        from app.modules.carbon.models import CarbonLog
        from app.modules.orders.models import Order
        
        store_ids = [store.id for store in stores]
        now = datetime.now(UTC)
        
        # 1. active_surplus count per store
        surplus_res = await self.db.execute(
            select(Product.store_id, func.count(Product.id))
            .filter(
                and_(
                    Product.store_id.in_(store_ids),
                    Product.stock > 0,
                    Product.expired_at > now
                )
            )
            .group_by(Product.store_id)
        )
        surplus_map = {row[0]: row[1] for row in surplus_res.all()}
        
        # 2. total_reviews count per store
        reviews_res = await self.db.execute(
            select(Review.store_id, func.count(Review.id))
            .filter(Review.store_id.in_(store_ids))
            .group_by(Review.store_id)
        )
        reviews_map = {row[0]: row[1] for row in reviews_res.all()}
        
        # 3. eco_impact_saved_meals (sum of sold count on products)
        meals_res = await self.db.execute(
            select(Product.store_id, func.sum(Product.sold))
            .filter(Product.store_id.in_(store_ids))
            .group_by(Product.store_id)
        )
        meals_map = {row[0]: int(row[1] or 0) for row in meals_res.all()}
        
        # 4. eco_impact_co2 (sum of carbon_saved_kg from carbon_logs of completed orders)
        co2_res = await self.db.execute(
            select(Order.store_id, func.sum(CarbonLog.carbon_saved_kg))
            .join(CarbonLog, CarbonLog.order_id == Order.id)
            .filter(Order.store_id.in_(store_ids))
            .group_by(Order.store_id)
        )
        co2_map = {row[0]: float(row[1] or 0.0) for row in co2_res.all()}
        
        # Inject dynamic properties to Store objects
        for store in stores:
            store.active_surplus = surplus_map.get(store.id, 0)
            store.total_reviews = reviews_map.get(store.id, 0)
            store.eco_impact_saved_meals = meals_map.get(store.id, 0)
            store.eco_impact_co2 = round(co2_map.get(store.id, 0.0), 1)

    async def get_store(self, store_id: uuid.UUID) -> Store | None:
        store = await self.repository.get_by_id(store_id)
        if store:
            await self._populate_store_stats([store])
        return store

    async def list_stores(self, skip: int = 0, limit: int = 100) -> Sequence[Store]:
        stores = await self.repository.get_multi(skip=skip, limit=limit)
        await self._populate_store_stats(list(stores))
        return stores

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
        items, total = await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )
        await self._populate_store_stats(list(items))
        return items, total


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
