import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: AsyncSession):
        self.repository = ProductRepository(db)

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self.repository.get_by_id(product_id)

    async def list_products(self, skip: int = 0, limit: int = 100) -> Sequence[Product]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def list_products_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Product], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )


    async def create_product(self, schema: ProductCreate) -> Product:
        product_data = schema.model_dump()
        return await self.repository.create(product_data)

    async def update_product(self, product_id: uuid.UUID, schema: ProductUpdate) -> Product:
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        product_data = schema.model_dump(exclude_unset=True)
        return await self.repository.update(product, product_data)

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        return await self.repository.delete(product_id)
