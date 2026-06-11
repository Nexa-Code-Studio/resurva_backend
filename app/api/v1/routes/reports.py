import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.summaries.schemas import DailySummaryResponse, MonthlySummaryResponse
from app.modules.summaries.service.summaries_service import SummaryService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.get("/store/{store_id}/daily", response_model=DailySummaryResponse)
async def get_daily(
    store_id: uuid.UUID,
    summary_date: date,
    db: AsyncSession = Depends(get_db_session)
):
    service = SummaryService(db)
    summary = await service.get_daily_summary(store_id, summary_date)
    if not summary:
        raise HTTPException(status_code=404, detail="Daily summary not found")
    return summary


@router.get("/store/{store_id}/monthly", response_model=list[MonthlySummaryResponse])
async def list_monthly(
    store_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db_session)
):
    service = SummaryService(db)
    return await service.get_monthly_summaries(store_id, year)


@router.get("/daily", response_model=PaginatedResponse[DailySummaryResponse])
async def list_daily_summaries_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = SummaryService(db)
    items, total = await service.list_daily_summaries_paginated(
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


@router.get("/monthly", response_model=PaginatedResponse[MonthlySummaryResponse])
async def list_monthly_summaries_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = SummaryService(db)
    items, total = await service.list_monthly_summaries_paginated(
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

