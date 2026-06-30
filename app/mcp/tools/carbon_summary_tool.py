from datetime import date, timedelta
import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.carbon.models import CarbonLog
from app.modules.orders.models import Order


class CarbonSummaryInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch carbon savings for")
    period: str = Field("month", description="Period to fetch carbon savings: today, week, month, all")


class CarbonSummaryTool(BaseMCPTool):
    name = "carbon_summary"
    description = "Retrieves total carbon emissions saved (kg CO2e) by preventing food waste at a store."
    input_schema = CarbonSummaryInput

    async def execute(self, db: AsyncSession, store_id: str, period: str = "month") -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        now = date.today()
        period_map = {
            "today": now,
            "week": now - timedelta(days=7),
            "month": now.replace(day=1),
            "all": None
        }
        since = period_map.get(period)

        q = select(func.sum(CarbonLog.carbon_saved_kg)).join(
            Order, Order.id == CarbonLog.order_id
        ).where(Order.store_id == store_uuid)

        if since:
            q = q.where(CarbonLog.created_at >= since)

        result = await db.execute(q)
        total = result.scalar() or 0.0

        return {
            "store_id": store_id,
            "period": period,
            "carbon_saved_kg": round(total, 2),
            "equivalent_trees_planted": round(total / 21.77, 1)  # 1 tree ~21.77 kg CO2/year
        }
