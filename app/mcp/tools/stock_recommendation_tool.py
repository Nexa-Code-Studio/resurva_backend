import uuid
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.products.models import Product
from app.modules.orders.models import Order, OrderItem
from app.core.enums import OrderStatus, UserRole


class StockRecommendationInput(BaseModel):
    store_id: str = Field(description="UUID of the store to get stock recommendations for")
    product_id: str | None = Field(None, description="Optional UUID of a specific product to restrict recommendation to")
    period_days: int = Field(14, description="Number of past days to average sales over")
    target_date: str | None = Field(None, description="Target date for forecasting in YYYY-MM-DD format (defaults to tomorrow)")
    weekend_multiplier: float = Field(1.2, description="Sales multiplier applied if the target date is on a weekend")


class StockRecommendationTool(BaseMCPTool):
    name = "stock_recommendation"
    description = (
        "Calculates recommended stock/production levels for products in a store for tomorrow or a target date. "
        "Averages daily sales over a prior period, adjusts for weekend factors, and subtracts current inventory."
    )
    input_schema = StockRecommendationInput
    allowed_roles = [UserRole.OWNER, UserRole.SELLER, UserRole.ADMIN]

    async def execute(
        self,
        db: AsyncSession,
        store_id: str,
        product_id: str | None = None,
        period_days: int = 14,
        target_date: str | None = None,
        weekend_multiplier: float = 1.2
    ) -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        product_uuid = uuid.UUID(product_id) if product_id else None

        if target_date:
            try:
                t_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Format target_date salah. Gunakan YYYY-MM-DD."}
        else:
            t_date = date.today() + timedelta(days=1)

        # target_dt is start of target_date (midnight) in UTC
        target_dt = datetime.combine(t_date, time.min).replace(tzinfo=timezone.utc)
        since_dt = datetime.combine(t_date - timedelta(days=period_days), time.min).replace(tzinfo=timezone.utc)

        # Check if target date is weekend (Saturday=5, Sunday=6)
        is_weekend = t_date.weekday() in (5, 6)
        multiplier = weekend_multiplier if is_weekend else 1.0

        # Query products and total sold in the period
        q = (
            select(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.stock.label("current_stock"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("total_sold")
            )
            .select_from(Product)
            .outerjoin(
                OrderItem,
                OrderItem.product_id == Product.id
            )
            .outerjoin(
                Order,
                and_(
                    Order.id == OrderItem.order_id,
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= since_dt,
                    Order.created_at < target_dt
                )
            )
            .where(Product.store_id == store_uuid)
        )
        if product_uuid:
            q = q.where(Product.id == product_uuid)

        q = q.group_by(Product.id, Product.name, Product.stock)
        
        res = await db.execute(q)
        rows = res.all()

        recommendations = []
        for row in rows:
            daily_avg = float(row.total_sold) / period_days
            adjusted_demand = daily_avg * multiplier
            rec_qty = max(0, math.ceil(adjusted_demand) - row.current_stock)
            
            recommendations.append({
                "product_id": str(row.product_id),
                "product_name": row.product_name,
                "current_stock": row.current_stock,
                "total_sold_in_period": int(row.total_sold),
                "daily_average_sales": round(daily_avg, 2),
                "adjusted_demand_forecast": math.ceil(adjusted_demand),
                "recommendation": rec_qty
            })

        return {
            "store_id": store_id,
            "target_date": str(t_date),
            "is_weekend": is_weekend,
            "multiplier_applied": multiplier,
            "period_days": period_days,
            "recommendations": recommendations
        }
