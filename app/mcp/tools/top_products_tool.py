from datetime import date, timedelta
import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.products.models import Product
from app.modules.orders.models import Order, OrderItem


class TopProductsInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch top products for")
    limit: int = Field(5, description="Maximum number of products to return")
    period_days: int = Field(30, description="Number of past days to aggregate sales for")


class TopProductsTool(BaseMCPTool):
    name = "top_products"
    description = "Retrieves the best-selling products in a store based on quantities sold in the last N days."
    input_schema = TopProductsInput

    async def execute(self, db: AsyncSession, store_id: str, limit: int = 5, period_days: int = 30) -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        since = date.today() - timedelta(days=period_days)

        q = (
            select(Product.name, func.sum(OrderItem.quantity).label("total_sold"))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Product.store_id == store_uuid,
                Order.created_at >= since,
                Order.status == "completed"
            )
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )

        result = await db.execute(q)
        rows = result.all()

        return {
            "store_id": store_id,
            "period_days": period_days,
            "products": [
                {
                    "name": r.name,
                    "total_sold": int(r.total_sold) if r.total_sold is not None else 0
                }
                for r in rows
            ]
        }
