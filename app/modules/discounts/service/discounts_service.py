import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.discounts.models import Discount
from app.modules.discounts.repository import DiscountRepository
from app.modules.discounts.schemas import DiscountCreate


class DiscountService:
    def __init__(self, db: AsyncSession):
        self.repository = DiscountRepository(db)

    async def create_discount(self, schema: DiscountCreate) -> Discount:
        return await self.repository.create(schema.model_dump())

    async def get_store_discounts(self, store_id: uuid.UUID) -> Sequence[Discount]:
        result = await self.repository.db.execute(
            select(Discount).filter(Discount.store_id == store_id)
        )
        return result.scalars().all()

    async def list_discounts_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Discount], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

