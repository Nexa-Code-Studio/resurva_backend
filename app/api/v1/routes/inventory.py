import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.inventory.schemas import (
    ExpiryAlertResponse,
    InventoryBatchCreate,
    InventoryBatchResponse,
    InventoryBatchUpdate,
    InventoryTransactionResponse,
)
from app.modules.inventory.service.inventory_service import InventoryService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.get("/store/{store_id}/batches", response_model=list[InventoryBatchResponse])
async def list_batches(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """List all inventory batches for a store."""
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
    """List inventory batches with pagination."""
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


@router.post("/batches", response_model=InventoryBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    schema: InventoryBatchCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new inventory batch. Automatically generates batch_tag and logs stock_in."""
    service = InventoryService(db)
    return await service.create_batch(schema)


@router.put("/batches/{batch_id}", response_model=InventoryBatchResponse)
async def update_batch(
    batch_id: uuid.UUID,
    schema: InventoryBatchUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update an inventory batch's quantity, expiry, or surplus start time."""
    service = InventoryService(db)
    batch = await service.update_batch(batch_id, schema)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete an inventory batch and log stock_out."""
    service = InventoryService(db)
    deleted = await service.delete_batch(batch_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")


@router.get("/store/{store_id}/expiry-alerts", response_model=list[ExpiryAlertResponse])
async def list_alerts(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """List expiry alerts for a store."""
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
    """List expiry alerts with pagination."""
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


@router.get("/stock-logs", response_model=PaginatedResponse[InventoryTransactionResponse])
async def get_stock_logs(
    store_id: uuid.UUID,
    product_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve stock movement history for a store, optionally filtered by product."""
    service = InventoryService(db)
    items, total = await service.get_stock_logs(
        store_id=store_id,
        product_id=product_id,
        page=page,
        page_size=page_size,
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
