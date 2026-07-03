import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: AsyncSession):
        self.repository = ProductRepository(db)

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        result = await self.repository.db.execute(
            select(Product)
            .filter(Product.id == product_id)
            .options(selectinload(Product.store))
        )
        return result.scalar_one_or_none()

    async def list_products(self, skip: int = 0, limit: int = 100) -> Sequence[Product]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def list_products_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        flash_sale: bool = False
    ) -> tuple[Sequence[Product], int]:
        from app.modules.inventory.models import InventoryBatch
        from sqlalchemy import func, select
        from datetime import datetime, UTC
        
        query = select(Product).options(selectinload(Product.store))
        
        if store_id is not None:
            query = query.where(Product.store_id == store_id)
            
        if flash_sale:
            now = datetime.now(UTC)
            query = query.join(InventoryBatch, Product.id == InventoryBatch.product_id).where(
                InventoryBatch.available_from <= now,
                InventoryBatch.expired_at > now,
                InventoryBatch.remaining_quantity > 0
            ).distinct()

        if sort_by and hasattr(Product, sort_by):
            col_attr = getattr(Product, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(col_attr.desc())
            else:
                query = query.order_by(col_attr.asc())
        else:
            query = query.order_by(Product.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        count_res = await self.repository.db.execute(count_query)
        total = count_res.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        res = await self.repository.db.execute(query)
        items = res.scalars().all()

        return items, total


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
