import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.modules.products.models import Product, ProductVariantGroup, ProductVariantOption
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate, ProductVariantGroupCreate, ProductVariantGroupUpdate, ProductVariantOptionCreate, ProductVariantOptionUpdate

class ProductService:
    def __init__(self, db: AsyncSession):
        self.repository = ProductRepository(db)

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        result = await self.repository.db.execute(
            select(Product)
            .filter(Product.id == product_id)
            .options(
                selectinload(Product.store),
                selectinload(Product.variant_groups).selectinload(ProductVariantGroup.options),
            )
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
        
        query = select(Product).options(
            selectinload(Product.store),
            selectinload(Product.variant_groups).selectinload(ProductVariantGroup.options),
        )
        
        if store_id is not None:
            query = query.where(Product.store_id == store_id)
            
        if flash_sale:
            now = datetime.now(UTC)
            query = query.join(InventoryBatch, Product.id == InventoryBatch.product_id).where(
                InventoryBatch.surplus_starts_at <= now,
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
        import json
        product_data = schema.model_dump(exclude={"variant_groups", "ingredients"})
        if schema.ingredients:
            product_data["ingredients_data"] = json.dumps(schema.ingredients)
        else:
            product_data["ingredients_data"] = None

        product = await self.repository.create(product_data)

        # Save nested variant groups
        for vg_schema in schema.variant_groups:
            group = ProductVariantGroup(
                id=uuid.uuid4(),
                product_id=product.id,
                name=vg_schema.name,
                is_required=vg_schema.is_required,
                max_selections=vg_schema.max_selections,
            )
            self.repository.db.add(group)
            await self.repository.db.flush()
            for opt_schema in vg_schema.options:
                option = ProductVariantOption(
                    id=uuid.uuid4(),
                    variant_group_id=group.id,
                    name=opt_schema.name,
                    additional_price=opt_schema.additional_price,
                )
                self.repository.db.add(option)

        await self.repository.db.commit()
        # Return fully loaded product with all variant groups & store eager loaded
        loaded_product = await self.get_product(product.id)
        if not loaded_product:
            return product
        return loaded_product

    async def update_product(self, product_id: uuid.UUID, schema: ProductUpdate) -> Product:
        import json
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        product_data = schema.model_dump(exclude_unset=True, exclude={"variant_groups", "ingredients"})
        if schema.ingredients is not None:
            product_data["ingredients_data"] = json.dumps(schema.ingredients)

        updated = await self.repository.update(product, product_data)

        # Replace nested variant groups if provided
        if schema.variant_groups is not None:
            from sqlalchemy import delete
            # Delete old variant groups (cascades to options)
            await self.repository.db.execute(
                delete(ProductVariantGroup).where(ProductVariantGroup.product_id == product_id)
            )
            # Insert new ones
            for vg_schema in schema.variant_groups:
                group = ProductVariantGroup(
                    id=uuid.uuid4(),
                    product_id=product_id,
                    name=vg_schema.name,
                    is_required=vg_schema.is_required,
                    max_selections=vg_schema.max_selections,
                )
                self.repository.db.add(group)
                await self.repository.db.flush()
                for opt_schema in vg_schema.options:
                    option = ProductVariantOption(
                        id=uuid.uuid4(),
                        variant_group_id=group.id,
                        name=opt_schema.name,
                        additional_price=opt_schema.additional_price,
                    )
                    self.repository.db.add(option)

        await self.repository.db.commit()
        # Return fully loaded product with all variant groups & store eager loaded
        loaded_product = await self.get_product(updated.id)
        if not loaded_product:
            return updated
        return loaded_product

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        return await self.repository.delete(product_id)

    # --- Variant Group CRUD ---

    async def list_variant_groups(self, product_id: uuid.UUID) -> list[ProductVariantGroup]:
        from sqlalchemy.orm import selectinload
        result = await self.repository.db.execute(
            select(ProductVariantGroup)
            .filter(ProductVariantGroup.product_id == product_id)
            .options(selectinload(ProductVariantGroup.options))
        )
        return list(result.scalars().all())

    async def create_variant_group(self, product_id: uuid.UUID, schema: ProductVariantGroupCreate) -> ProductVariantGroup:
        group = ProductVariantGroup(
            id=uuid.uuid4(),
            product_id=product_id,
            name=schema.name,
            is_required=schema.is_required,
            max_selections=schema.max_selections,
        )
        self.repository.db.add(group)
        await self.repository.db.flush()
        # Create options
        for opt_schema in schema.options:
            option = ProductVariantOption(
                id=uuid.uuid4(),
                variant_group_id=group.id,
                name=opt_schema.name,
                additional_price=opt_schema.additional_price,
            )
            self.repository.db.add(option)
        await self.repository.db.commit()
        await self.repository.db.refresh(group)
        return group

    async def update_variant_group(self, group_id: uuid.UUID, schema: ProductVariantGroupUpdate) -> ProductVariantGroup | None:
        result = await self.repository.db.execute(
            select(ProductVariantGroup).filter(ProductVariantGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            return None
        data = schema.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(group, field, value)
        self.repository.db.add(group)
        await self.repository.db.commit()
        await self.repository.db.refresh(group)
        return group

    async def delete_variant_group(self, group_id: uuid.UUID) -> bool:
        result = await self.repository.db.execute(
            select(ProductVariantGroup).filter(ProductVariantGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            return False
        await self.repository.db.delete(group)
        await self.repository.db.commit()
        return True

    # --- Variant Option CRUD ---

    async def create_variant_option(self, group_id: uuid.UUID, schema: ProductVariantOptionCreate) -> ProductVariantOption:
        option = ProductVariantOption(
            id=uuid.uuid4(),
            variant_group_id=group_id,
            name=schema.name,
            additional_price=schema.additional_price,
        )
        self.repository.db.add(option)
        await self.repository.db.commit()
        await self.repository.db.refresh(option)
        return option

    async def delete_variant_option(self, option_id: uuid.UUID) -> bool:
        result = await self.repository.db.execute(
            select(ProductVariantOption).filter(ProductVariantOption.id == option_id)
        )
        option = result.scalar_one_or_none()
        if not option:
            return False
        await self.repository.db.delete(option)
        await self.repository.db.commit()
        return True
