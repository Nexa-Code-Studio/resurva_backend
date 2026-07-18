import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.repository import ExpiryAlertRepository, InventoryBatchRepository
from app.modules.inventory.models import ExpiryAlert, InventoryBatch, InventoryTransaction
from app.modules.inventory.schemas import InventoryBatchCreate, InventoryBatchUpdate
from app.modules.products.models import Product


def _generate_batch_tag(sku: str, expired_at: datetime, suffix_letter: str) -> str:
    """Generate a tag in format: {SKU}-{DDMMYYYY}-{A/B/C...}"""
    date_str = expired_at.strftime("%d%m%Y")
    return f"{sku}-{date_str}-{suffix_letter}"


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.batch_repo = InventoryBatchRepository(db)
        self.alert_repo = ExpiryAlertRepository(db)
        self.db = db

    async def get_store_batches(self, store_id: uuid.UUID) -> Sequence[InventoryBatch]:
        result = await self.batch_repo.db.execute(
            select(InventoryBatch).filter(InventoryBatch.store_id == store_id)
        )
        return result.scalars().all()

    async def get_store_expiry_alerts(self, store_id: uuid.UUID) -> Sequence[ExpiryAlert]:
        result = await self.alert_repo.db.execute(
            select(ExpiryAlert).filter(ExpiryAlert.store_id == store_id)
        )
        return result.scalars().all()

    async def list_batches_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[InventoryBatch], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.batch_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def list_alerts_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[ExpiryAlert], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.alert_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def get_batch(self, batch_id: uuid.UUID) -> InventoryBatch | None:
        return await self.batch_repo.get_by_id(batch_id)

    async def create_batch(self, schema: InventoryBatchCreate) -> InventoryBatch:
        # Look up product SKU for the batch tag
        prod_result = await self.db.execute(
            select(Product.sku).filter(Product.id == schema.product_id)
        )
        sku = prod_result.scalar_one_or_none() or "PRD"

        # Find how many batches already exist for this product with the same expiry date
        # to determine the next suffix letter
        date_str = schema.expired_at.strftime("%d%m%Y")
        count_result = await self.db.execute(
            select(func.count()).filter(
                InventoryBatch.product_id == schema.product_id,
                InventoryBatch.batch_tag.like(f"{sku}-{date_str}-%")
            )
        )
        count = count_result.scalar_one() or 0
        suffix = chr(65 + count)  # A, B, C, ...
        batch_tag = _generate_batch_tag(sku, schema.expired_at, suffix)

        batch = InventoryBatch(
            id=uuid.uuid4(),
            product_id=schema.product_id,
            store_id=schema.store_id,
            quantity=schema.quantity,
            remaining_quantity=schema.remaining_quantity,
            expired_at=schema.expired_at,
            surplus_starts_at=schema.surplus_starts_at,
            batch_tag=batch_tag,
        )
        self.db.add(batch)

        # Update parent product stock
        prod = await self.db.get(Product, schema.product_id)
        if prod:
            prod.stock += schema.quantity
            self.db.add(prod)

        await self.db.flush()  # get the batch id

        # Log stock-in transaction
        txn = InventoryTransaction(
            id=uuid.uuid4(),
            product_id=schema.product_id,
            store_id=schema.store_id,
            inventory_batch_id=batch.id,
            batch_tag=batch_tag,
            type="stock_in",
            quantity=schema.quantity,
            reason="New batch created",
        )
        self.db.add(txn)
        await self.db.commit()
        await self.db.refresh(batch)
        return batch

    async def update_batch(self, batch_id: uuid.UUID, schema: InventoryBatchUpdate) -> InventoryBatch | None:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            return None

        old_qty = batch.remaining_quantity
        update_data = schema.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(batch, field, value)
        self.db.add(batch)

        # Log adjustment if remaining_quantity changed
        new_qty = batch.remaining_quantity
        delta = new_qty - old_qty
        if delta != 0:
            # Sync parent product stock
            prod = await self.db.get(Product, batch.product_id)
            if prod:
                prod.stock += delta
                if prod.stock < 0:
                    prod.stock = 0
                self.db.add(prod)

            txn = InventoryTransaction(
                id=uuid.uuid4(),
                product_id=batch.product_id,
                store_id=batch.store_id,
                inventory_batch_id=batch.id,
                batch_tag=batch.batch_tag,
                type="adjustment",
                quantity=delta,
                reason="Batch quantity updated",
            )
            self.db.add(txn)

        await self.db.commit()
        await self.db.refresh(batch)
        return batch

    async def delete_batch(self, batch_id: uuid.UUID) -> bool:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            return False

        # Log deletion
        txn = InventoryTransaction(
            id=uuid.uuid4(),
            product_id=batch.product_id,
            store_id=batch.store_id,
            inventory_batch_id=None,
            batch_tag=batch.batch_tag,
            type="stock_out",
            quantity=-batch.remaining_quantity,
            reason="Batch deleted",
        )
        self.db.add(txn)

        # Sync parent product stock
        prod = await self.db.get(Product, batch.product_id)
        if prod:
            prod.stock -= batch.remaining_quantity
            if prod.stock < 0:
                prod.stock = 0
            self.db.add(prod)

        await self.db.delete(batch)
        await self.db.commit()
        return True

    async def get_stock_logs(
        self,
        store_id: uuid.UUID,
        product_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[Sequence[InventoryTransaction], int]:
        query = select(InventoryTransaction).filter(
            InventoryTransaction.store_id == store_id
        ).order_by(InventoryTransaction.created_at.desc())

        count_query = select(func.count()).filter(
            InventoryTransaction.store_id == store_id
        )

        if product_id:
            query = query.filter(InventoryTransaction.product_id == product_id)
            count_query = count_query.filter(InventoryTransaction.product_id == product_id)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        return result.scalars().all(), count_result.scalar_one()
