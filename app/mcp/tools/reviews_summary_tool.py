import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.reviews.models import Review


class ReviewsSummaryInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch reviews for")
    product_id: str | None = Field(None, description="Optional UUID of a specific product to filter reviews by")
    limit: int = Field(5, description="Maximum number of recent reviews to return")


class ReviewsSummaryTool(BaseMCPTool):
    name = "reviews_summary"
    description = "Retrieves a summary of customer reviews for a store, including average rating and recent review snippets."
    input_schema = ReviewsSummaryInput

    async def execute(self, db: AsyncSession, store_id: str, product_id: str | None = None, limit: int = 5) -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        product_uuid = uuid.UUID(product_id) if product_id else None

        # Get average rating and total count
        avg_q = select(func.avg(Review.rating), func.count(Review.id)).where(Review.store_id == store_uuid)
        if product_uuid:
            avg_q = avg_q.where(Review.product_id == product_uuid)
            
        avg_res = await db.execute(avg_q)
        avg_rating, total_count = avg_res.one()

        # Get recent reviews
        recent_q = (
            select(Review)
            .where(Review.store_id == store_uuid)
        )
        if product_uuid:
            recent_q = recent_q.where(Review.product_id == product_uuid)
            
        recent_q = recent_q.order_by(Review.created_at.desc()).limit(limit)
        recent_res = await db.execute(recent_q)
        reviews = recent_res.scalars().all()

        return {
            "store_id": store_id,
            "product_id": product_id,
            "avg_rating": round(avg_rating or 0.0, 1),
            "total_reviews": total_count,
            "recent_reviews": [
                {
                    "rating": r.rating,
                    "label": r.label,
                    "snippet": r.description[:100] if r.description else "",
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in reviews
            ]
        }
