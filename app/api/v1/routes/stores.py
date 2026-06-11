import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.stores.schemas import StoreCreate, StoreResponse, StoreUpdate
from app.modules.stores.service.stores_service import StoreService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    schema: StoreCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new retail Store and initialize its Wallet."""
    service = StoreService(db)
    return await service.create_store(schema)


@router.get("/", response_model=PaginatedResponse[StoreResponse])
async def list_stores(
    page: int = 1,
    page_size: int = 20,
    business_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve multiple stores with pagination."""
    service = StoreService(db)
    items, total = await service.list_stores_paginated(
        page=page,
        page_size=page_size,
        business_id=business_id,
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



@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve details of a single Store by UUID."""
    service = StoreService(db)
    store = await service.get_store(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    return store


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: uuid.UUID,
    schema: StoreUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update details of a Store."""
    service = StoreService(db)
    return await service.update_store(store_id, schema)


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a Store."""
    service = StoreService(db)
    deleted = await service.delete_store(store_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
