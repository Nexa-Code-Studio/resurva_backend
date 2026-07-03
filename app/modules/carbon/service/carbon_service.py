from collections.abc import Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.carbon.models import CarbonLog
from app.modules.carbon.repository import CarbonRepository


class CarbonService:
    def __init__(self, db: AsyncSession):
        self.repository = CarbonRepository(db)

    async def log_carbon_saving(self, order_id: uuid.UUID, user_id: uuid.UUID, carbon_saved: float) -> CarbonLog:
        return await self.repository.create({
            "order_id": order_id,
            "user_id": user_id,
            "carbon_saved_kg": carbon_saved
        })

    async def get_user_total_savings(self, user_id: uuid.UUID) -> float:
        result = await self.repository.db.execute(
            select(func.sum(CarbonLog.carbon_saved_kg)).filter(CarbonLog.user_id == user_id)
        )
        return result.scalar() or 0.0

    async def get_user_sustainability_stats(self, user_id: uuid.UUID) -> dict:
        from sqlalchemy import select, func
        from app.core.enums import OrderStatus
        from app.modules.carbon.models import CarbonLog
        from app.modules.orders.models import Order, OrderItem

        # 1. Total CO2 saved
        co2_res = await self.repository.db.execute(
            select(func.sum(CarbonLog.carbon_saved_kg)).filter(CarbonLog.user_id == user_id)
        )
        co2_saved = co2_res.scalar() or 0.0

        # 2. Total items/meals saved (sum of quantity of completed orders)
        meals_res = await self.repository.db.execute(
            select(func.sum(OrderItem.quantity))
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.user_id == user_id, Order.status == OrderStatus.COMPLETED)
        )
        meals_saved = meals_res.scalar() or 0

        # Convert meals saved count to estimated kg (e.g. 0.5 kg per meal)
        food_saved_kg = meals_saved * 0.5

        # Avoided emissions metaphor: co2_saved * 4.1 (km equivalent of standard car driving)
        emissions_avoided_km = co2_saved * 4.1

        return {
            "co2_saved_kg": round(co2_saved, 2),
            "food_saved_kg": round(food_saved_kg, 2),
            "meals_saved_count": meals_saved,
            "emissions_avoided_km": round(emissions_avoided_km, 2)
        }

    async def list_carbon_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[CarbonLog], int]:
        filters = {}
        if user_id is not None:
            filters["user_id"] = user_id
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

