import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.products.schemas import (
    ProductCreate, ProductResponse, ProductUpdate,
    ProductVariantGroupCreate, ProductVariantGroupResponse,
    ProductVariantGroupUpdate, ProductVariantOptionCreate, ProductVariantOptionResponse,
)
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
    flash_sale: bool = False,
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve multiple products with pagination."""
    service = ProductService(db)
    items, total = await service.list_products_paginated(
        page=page,
        page_size=page_size,
        store_id=store_id,
        sort_by=sort_by,
        sort_order=sort_order,
        flash_sale=flash_sale,
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


@router.get("/{product_id}/variants", response_model=list[ProductVariantGroupResponse])
async def list_product_variants(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """List all variant groups (with options) for a product."""
    service = ProductService(db)
    return await service.list_variant_groups(product_id)


@router.post("/{product_id}/variants", response_model=ProductVariantGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_variant_group(
    product_id: uuid.UUID,
    schema: ProductVariantGroupCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a variant group with options for a product."""
    service = ProductService(db)
    return await service.create_variant_group(product_id, schema)


@router.put("/variants/{group_id}", response_model=ProductVariantGroupResponse)
async def update_variant_group(
    group_id: uuid.UUID,
    schema: ProductVariantGroupUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a variant group."""
    service = ProductService(db)
    group = await service.update_variant_group(group_id, schema)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant group not found")
    return group


@router.delete("/variants/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a variant group and all its options."""
    service = ProductService(db)
    deleted = await service.delete_variant_group(group_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant group not found")


@router.post("/variants/{group_id}/options", response_model=ProductVariantOptionResponse, status_code=status.HTTP_201_CREATED)
async def create_variant_option(
    group_id: uuid.UUID,
    schema: ProductVariantOptionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Add a new option to an existing variant group."""
    service = ProductService(db)
    return await service.create_variant_option(group_id, schema)


@router.delete("/variants/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant_option(
    option_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a variant option."""
    service = ProductService(db)
    deleted = await service.delete_variant_option(option_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant option not found")


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
    file_url = storage.get_file_url(file_path)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "storage_path": file_path,
        "access_url": file_url
    }
