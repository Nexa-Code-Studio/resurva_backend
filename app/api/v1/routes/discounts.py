import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.discounts.schemas import DiscountCreate, DiscountResponse
from app.modules.discounts.service.discounts_service import DiscountService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.post("/", response_model=DiscountResponse)
async def create_discount(
    schema: DiscountCreate,
    db: AsyncSession = Depends(get_db_session)
):
    service = DiscountService(db)
    return await service.create_discount(schema)


@router.get("/store/{store_id}", response_model=list[DiscountResponse])
async def list_store_discounts(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = DiscountService(db)
    return await service.get_store_discounts(store_id)


@router.get("/", response_model=PaginatedResponse[DiscountResponse])
async def list_discounts_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = DiscountService(db)
    items, total = await service.list_discounts_paginated(
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

