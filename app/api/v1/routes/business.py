import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.business.schemas import BusinessCreate, BusinessResponse
from app.modules.business.service.business_service import BusinessService

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.post("/", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
async def create_business(
    schema: BusinessCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new Business entity."""
    service = BusinessService(db)
    return await service.create_business(schema)


@router.get("/", response_model=PaginatedResponse[BusinessResponse])
async def list_businesses(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    """List all Business entities."""
    service = BusinessService(db)
    items, total = await service.list_businesses_paginated(
        page=page,
        page_size=page_size,
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



@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a Business entity details."""
    service = BusinessService(db)
    business = await service.get_business(business_id)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    return business
