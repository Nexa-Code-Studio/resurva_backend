import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.inventory.schemas import ExpiryAlertResponse, InventoryBatchResponse
from app.modules.inventory.service.inventory_service import InventoryService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.get("/store/{store_id}/batches", response_model=list[InventoryBatchResponse])
async def list_batches(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = InventoryService(db)
    return await service.get_store_batches(store_id)


@router.get("/batches", response_model=PaginatedResponse[InventoryBatchResponse])
async def list_batches_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = InventoryService(db)
    items, total = await service.list_batches_paginated(
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


@router.get("/store/{store_id}/expiry-alerts", response_model=list[ExpiryAlertResponse])
async def list_alerts(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = InventoryService(db)
    return await service.get_store_expiry_alerts(store_id)


@router.get("/expiry-alerts", response_model=PaginatedResponse[ExpiryAlertResponse])
async def list_alerts_paginated(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = InventoryService(db)
    items, total = await service.list_alerts_paginated(
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

