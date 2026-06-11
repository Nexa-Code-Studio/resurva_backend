import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.products.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.modules.products.service.products_service import ProductService
from app.storage.factory import StorageFactory

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    schema: ProductCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new waste marketplace product."""
    service = ProductService(db)
    return await service.create_product(schema)


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve multiple products with pagination."""
    service = ProductService(db)
    items, total = await service.list_products_paginated(
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



@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve details of a single product by UUID."""
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    schema: ProductUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update details of a product."""
    service = ProductService(db)
    return await service.update_product(product_id, schema)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a product from the marketplace."""
    service = ProductService(db)
    deleted = await service.delete_product(product_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )


@router.post("/upload-image", status_code=status.HTTP_200_OK)
async def upload_product_image(
    file: UploadFile = File(...)
):
    """
    Upload product image utilizing the configured Storage Service.
    Saves to local/S3/MinIO and returns the access URL.
    """
    content = await file.read()
    storage = StorageFactory.get_storage_provider()

    # Save the file using Storage provider
    file_path = await storage.upload_file(
        file_content=content,
        filename=file.filename or "unknown",
        folder="products"
    )

    # Resolve public access URL
    file_url = await storage.get_file_url(file_path)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "storage_path": file_path,
        "access_url": file_url
    }
