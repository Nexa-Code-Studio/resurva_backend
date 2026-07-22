import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.reviews.models import Review
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import ReviewCreate


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.repository = ReviewRepository(db)

    async def create_review(self, user_id: uuid.UUID, schema: ReviewCreate) -> Review:
        data = schema.model_dump()
        data["user_id"] = user_id
        review = await self.repository.create(data)
        await self.repository.db.refresh(review, attribute_names=["user", "product"])
        return review

    async def get_store_reviews(self, store_id: uuid.UUID) -> Sequence[Review]:
        result = await self.repository.db.execute(
            select(Review)
            .options(selectinload(Review.user), selectinload(Review.product))
            .filter(Review.store_id == store_id)
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
            sort_order=sort_order,
            options=[selectinload(Review.user), selectinload(Review.product)]
        )

    async def get_reviews_summary(self, store_id: uuid.UUID) -> dict:
        reviews = await self.get_store_reviews(store_id)
        if not reviews:
            return {
                "summary": "Belum ada ulasan untuk toko ini.",
                "avg_rating": 0.0,
                "total_reviews": 0
            }
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        summary = f"Rangkuman Ulasan: Pelanggan secara keseluruhan memberikan penilaian sangat baik (rata-rata {avg_rating:.1f}/5) dari {len(reviews)} ulasan."
        return {
            "summary": summary,
            "avg_rating": round(avg_rating, 2),
            "total_reviews": len(reviews)
        }

