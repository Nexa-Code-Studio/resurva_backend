import uuid

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.stores.schemas import (
    StoreCreate,
    StoreResponse,
    StoreUpdate,
    EnterpriseRequestCreate,
    EnterpriseRequestResponse,
    ResetPasswordSchema,
)

from app.modules.stores.service.stores_service import StoreService
from app.storage.factory import StorageFactory

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
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve multiple stores with pagination."""
    service = StoreService(db)
    items, total = await service.list_stores_paginated(
        page=page,
        page_size=page_size,
        business_id=business_id,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search
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



@router.get("/categories", response_model=list[str])
async def list_store_categories(
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve all unique store categories."""
    service = StoreService(db)
    return await service.list_categories()


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


@router.post("/upload-image", status_code=status.HTTP_200_OK)
async def upload_store_image(
    file: UploadFile = File(...)
):
    """
    Upload store image utilizing the configured Storage Service.
    Saves to local/S3/MinIO and returns the access URL.
    """
    content = await file.read()
    storage = StorageFactory.get_storage_provider()

    # Save the file using Storage provider
    file_path = await storage.upload_file(
        file_content=content,
        filename=file.filename or "unknown",
        folder="stores"
    )

    # Resolve public access URL
    file_url = storage.get_file_url(file_path)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "storage_path": file_path,
        "access_url": file_url
    }


@router.post("/{store_id}/enterprise-requests", response_model=EnterpriseRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_enterprise_request(
    store_id: uuid.UUID,
    schema: EnterpriseRequestCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new Enterprise registration request for a Store."""
    service = StoreService(db)
    store = await service.get_store(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    return await service.create_enterprise_request(store_id, schema)


@router.post("/{store_id}/reset-seller-password", status_code=status.HTTP_200_OK)
async def reset_seller_password(
    store_id: uuid.UUID,
    schema: ResetPasswordSchema,
    db: AsyncSession = Depends(get_db_session)
):
    """Reset the password for the primary merchant/seller user associated with a store."""
    service = StoreService(db)
    await service.reset_seller_password(store_id, schema.new_password)
    return {"status": "success", "message": "Password merchant berhasil diperbarui."}


