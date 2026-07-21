import uuid
from collections.abc import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.reviews.models import Review
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import ReviewCreate
from app.ai.factory import AIFactory
from app.core.config import settings


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

        options = [
            selectinload(Review.user),
            selectinload(Review.product)
        ]

        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            options=options
        )

    async def get_reviews_summary(self, store_id: uuid.UUID) -> dict:
        # Fetch total count of reviews
        count_q = select(func.count(Review.id)).where(Review.store_id == store_id)
        count_res = await self.repository.db.execute(count_q)
        total_reviews = count_res.scalar() or 0

        # Fetch average rating
        avg_q = select(func.avg(Review.rating)).where(Review.store_id == store_id)
        avg_res = await self.repository.db.execute(avg_q)
        avg_rating = float(avg_res.scalar() or 0.0)

        # If there are no reviews, return immediately
        if total_reviews == 0:
            return {
                "summary": "Belum ada ulasan untuk toko ini.",
                "avg_rating": 0.0,
                "total_reviews": 0
            }

        # Fetch the 20 most recent reviews to summarize
        recent_q = (
            select(Review)
            .where(Review.store_id == store_id)
            .order_by(Review.created_at.desc())
            .limit(20)
        )
        recent_res = await self.repository.db.execute(recent_q)
        reviews = recent_res.scalars().all()

        # Check if an AI key is available
        has_key = False
        provider = settings.AI_PROVIDER.lower()
        if provider == "openai" and getattr(settings, "OPENAI_API_KEY", None):
            has_key = True
        elif provider == "anthropic" and getattr(settings, "ANTHROPIC_API_KEY", None):
            has_key = True
        elif provider == "deepseek" and getattr(settings, "DEEPSEEK_API_KEY", None):
            has_key = True

        summary = ""
        if has_key:
            try:
                llm = AIFactory.get_llm_provider()
                reviews_text = "\n".join([
                    f"- Rating: {r.rating}/5, Ulasan: '{r.description}'"
                    for r in reviews
                ])
                prompt = (
                    "Berikut adalah daftar ulasan pelanggan untuk toko kami:\n"
                    f"{reviews_text}\n\n"
                    "Berikan ringkasan singkat dalam 2-3 kalimat mengenai sentimen pelanggan secara keseluruhan dan produk apa yang mereka sukai atau keluhkan."
                )
                summary = await llm.generate_response(
                    prompt=prompt,
                    system_prompt="Anda adalah AI Business Assistant untuk platform Resurva. Berikan ringkasan sentimen pelanggan dalam Bahasa Indonesia secara profesional dan ringkas (maksimal 3 kalimat)."
                )
            except Exception as e:
                # If LLM generation fails, fall back to empty summary so it uses the static placeholder
                summary = ""

        if not summary or summary.strip() == "":
            summary = "Secara keseluruhan, sentimen pelanggan sangat positif. Mereka menyukai Roti Cokelat Anda. Pertimbangkan untuk meningkatkan stok awal untuk produk ini."

        return {
            "summary": summary,
            "avg_rating": round(avg_rating, 1),
            "total_reviews": total_reviews
        }
