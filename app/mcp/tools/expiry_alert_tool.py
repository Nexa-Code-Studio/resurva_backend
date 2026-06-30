import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ExpiryAlertStatus
from app.mcp.base_tool import BaseMCPTool
from app.modules.inventory.models import ExpiryAlert


class ExpiryAlertInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch expiry alerts for")
    critical_only: bool = Field(False, description="If True, only fetches critically close or already expired items")


class ExpiryAlertTool(BaseMCPTool):
    name = "expiry_alerts"
    description = "Retrieves active warnings and critical warnings for products nearing their expiration dates."
    input_schema = ExpiryAlertInput

    async def execute(self, db: AsyncSession, store_id: str, critical_only: bool = False) -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        q = select(ExpiryAlert).options(selectinload(ExpiryAlert.product)).where(ExpiryAlert.store_id == store_uuid)

        if critical_only:
            q = q.where(ExpiryAlert.status.in_([ExpiryAlertStatus.CRITICAL, ExpiryAlertStatus.EXPIRED]))

        # Limit to avoid huge outputs
        q = q.order_by(ExpiryAlert.alerted_at.desc()).limit(50)

        result = await db.execute(q)
        alerts = result.scalars().all()

        from app.modules.inventory.models import InventoryBatch

        alert_list = []
        for alert in alerts:
            p = alert.product
            if not p:
                continue

            # Fetch active batches for this product in this store
            batch_q = select(InventoryBatch).where(
                InventoryBatch.product_id == p.id,
                InventoryBatch.store_id == store_uuid,
                InventoryBatch.remaining_quantity > 0
            ).order_by(InventoryBatch.expired_at)

            batch_res = await db.execute(batch_q)
            batches = batch_res.scalars().all()

            alert_list.append({
                "product_id": str(p.id),
                "product_name": p.name,
                "original_price": p.original_price,
                "discounted_price": p.discounted_price,
                "days_until_expiry": alert.days_until_expiry,
                "status": alert.status.value,
                "alerted_at": alert.alerted_at.isoformat(),
                "batches": [
                    {
                        "batch_id": str(b.id),
                        "remaining_quantity": b.remaining_quantity,
                        "expired_at": b.expired_at.isoformat()
                    }
                    for b in batches
                ]
            })

        return {
            "store_id": store_id,
            "alerts": alert_list
        }
