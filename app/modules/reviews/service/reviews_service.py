import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reviews.models import Review
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import ReviewCreate


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.repository = ReviewRepository(db)

    async def create_review(self, user_id: uuid.UUID, schema: ReviewCreate) -> Review:
        data = schema.model_dump()
        data["user_id"] = user_id
        return await self.repository.create(data)

    async def get_store_reviews(self, store_id: uuid.UUID) -> Sequence[Review]:
        result = await self.repository.db.execute(
            select(Review).filter(Review.store_id == store_id)
        )
        return result.scalars().all()

    async def list_reviews_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Review], int]:
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

