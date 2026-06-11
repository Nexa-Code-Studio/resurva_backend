import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.carbon.schemas import CarbonLogResponse
from app.modules.carbon.service.carbon_service import CarbonService
from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.get("/carbon-logs", response_model=PaginatedResponse[CarbonLogResponse])
async def list_carbon_logs_paginated(
    page: int = 1,
    page_size: int = 20,
    user_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = CarbonService(db)
    items, total = await service.list_carbon_logs_paginated(
        page=page,
        page_size=page_size,
        user_id=user_id,
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
