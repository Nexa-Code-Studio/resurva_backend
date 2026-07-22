import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService
from app.modules.users.models import User
from app.modules.reviews.schemas import ReviewResponse, ReviewSummaryResponse, ReviewsSummaryResponse, ReviewCreate
from app.modules.reviews.service.reviews_service import ReviewService
from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.post("/", response_model=ReviewResponse)
async def create_review(
    schema: ReviewCreate,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = ReviewService(db)
    return await service.create_review(user_id=current_user.id, schema=schema)


@router.get("/summary", response_model=ReviewsSummaryResponse)
async def get_reviews_summary(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = ReviewService(db)
    return await service.get_reviews_summary(store_id=store_id)


@router.get("/", response_model=PaginatedResponse[ReviewResponse])
async def list_reviews_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = ReviewService(db)
    items, total = await service.list_reviews_paginated(
        page=page,
        page_size=page_size,
        store_id=store_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=list(items),
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )
