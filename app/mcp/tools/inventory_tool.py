from datetime import datetime, UTC
import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.inventory.models import InventoryBatch


class InventoryToolInput(BaseModel):
    product_id: str = Field(description="UUID of the product to check inventory for")
    store_id: str = Field(description="UUID of the store holding the inventory")


class InventoryTool(BaseMCPTool):
    name = "check_inventory"
    description = "Checks the available stock batches and quantities for a product in a store."
    input_schema = InventoryToolInput

    async def execute(self, db: AsyncSession, product_id: str, store_id: str) -> dict[str, Any]:
        product_uuid = uuid.UUID(product_id)
        store_uuid = uuid.UUID(store_id)

        q = select(InventoryBatch).where(
            InventoryBatch.product_id == product_uuid,
            InventoryBatch.store_id == store_uuid,
            InventoryBatch.remaining_quantity > 0,
            InventoryBatch.expired_at > datetime.now(UTC)
        ).order_by(InventoryBatch.expired_at)

        result = await db.execute(q)
        batches = result.scalars().all()

        return {
            "product_id": product_id,
            "store_id": store_id,
            "batches": [
                {
                    "batch_id": str(batch.id),
                    "quantity": batch.quantity,
                    "remaining_quantity": batch.remaining_quantity,
                    "expired_at": batch.expired_at.isoformat()
                }
                for batch in batches
            ]
        }
