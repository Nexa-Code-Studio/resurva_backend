import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business.models import Business
from app.modules.business.repository import BusinessRepository
from app.modules.business.schemas import BusinessCreate, BusinessUpdate


class BusinessService:
    def __init__(self, db: AsyncSession):
        self.repository = BusinessRepository(db)

    async def get_business(self, business_id: uuid.UUID) -> Business | None:
        return await self.repository.get_by_id(business_id)

    async def list_businesses(self, skip: int = 0, limit: int = 100) -> Sequence[Business]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def list_businesses_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Business], int]:
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )


    async def create_business(self, schema: BusinessCreate) -> Business:
        return await self.repository.create(schema.model_dump())

    async def update_business(self, business_id: uuid.UUID, schema: BusinessUpdate) -> Business | None:
        business = await self.repository.get_by_id(business_id)
        if not business:
            return None
        return await self.repository.update(business, schema.model_dump(exclude_unset=True))

    async def delete_business(self, business_id: uuid.UUID) -> bool:
        return await self.repository.delete(business_id)
