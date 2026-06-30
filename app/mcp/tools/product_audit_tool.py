import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.products.models import Product
from app.modules.orders.models import Order, OrderItem
from app.modules.reviews.models import Review
from app.core.enums import OrderStatus, UserRole


class ProductAuditInput(BaseModel):
    store_id: str = Field(description="UUID of the store to audit products for")
    product_id: str | None = Field(None, description="Optional UUID of a specific product to audit")
    period_days: int = Field(30, description="Number of past days to analyze sales and efficiency over")


class ProductAuditTool(BaseMCPTool):
    name = "product_audit"
    description = (
        "Audits products in a store by calculating a score from 0-100 based on Sales Volume (40%), "
        "Customer Ratings (30%), and Stock Efficiency (30%). Flags underperforming products for review."
    )
    input_schema = ProductAuditInput
    allowed_roles = [UserRole.OWNER, UserRole.SELLER, UserRole.ADMIN]

    async def execute(
        self,
        db: AsyncSession,
        store_id: str,
        product_id: str | None = None,
        period_days: int = 30
    ) -> dict[str, Any]:
        import json
        from app.core.redis import get_redis_client

        cache_key = f"cache:product_audit:{store_id}:{product_id or 'all'}:{period_days}"
        try:
            redis_client = await get_redis_client()
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            redis_client = None

        store_uuid = uuid.UUID(store_id)
        product_uuid = uuid.UUID(product_id) if product_id else None
        since_dt = datetime.now(timezone.utc) - timedelta(days=period_days)

        # 1. Fetch sales data for all products in the store to establish baseline (for Sales Score normalization)
        sales_q = (
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
                    Order.created_at >= since_dt
                )
            )
            .where(Product.store_id == store_uuid)
            .group_by(Product.id, Product.name, Product.stock)
        )
        sales_res = await db.execute(sales_q)
        sales_rows = sales_res.all()

        if not sales_rows:
            return {
                "store_id": store_id,
                "period_days": period_days,
                "audits": [],
                "message": "Tidak ada produk terdaftar untuk toko ini."
            }

        product_data = {}
        max_sales = 0
        for r in sales_rows:
            sold = int(r.total_sold)
            product_data[r.product_id] = {
                "product_name": r.product_name,
                "current_stock": r.current_stock,
                "total_sold": sold
            }
            if sold > max_sales:
                max_sales = sold

        # 2. Fetch rating summaries per product
        rating_q = (
            select(
                Review.product_id,
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("review_count")
            )
            .where(Review.store_id == store_uuid)
            .group_by(Review.product_id)
        )
        rating_res = await db.execute(rating_q)
        rating_rows = rating_res.all()

        product_ratings = {
            r.product_id: (float(r.avg_rating), int(r.review_count))
            for r in rating_rows
            if r.product_id is not None
        }

        # 3. Fetch store average rating as fallback
        store_rating_q = select(func.avg(Review.rating)).where(Review.store_id == store_uuid)
        store_rating_res = await db.execute(store_rating_q)
        store_avg_val = store_rating_res.scalar()
        store_avg = float(store_avg_val) if store_avg_val is not None else 5.0

        audits = []
        for p_id, p_info in product_data.items():
            if product_uuid and p_id != product_uuid:
                continue

            # Sales Score (40%) - Normalized relative to top-selling product
            sold = p_info["total_sold"]
            sales_score = (sold / max_sales) * 100.0 if max_sales > 0 else 0.0

            # Rating Score (30%) - Normalized relative to 5.0 stars
            if p_id in product_ratings:
                avg_rating, count = product_ratings[p_id]
                rating_score = (avg_rating / 5.0) * 100.0
            else:
                avg_rating, count = store_avg, 0
                rating_score = (store_avg / 5.0) * 100.0

            # Stock Efficiency Score (30%)
            stock = p_info["current_stock"]
            avg_daily = sold / period_days
            if avg_daily > 0:
                overstock_ratio = stock / (avg_daily * 3.0)
                efficiency_score = max(0.0, 100.0 - overstock_ratio * 50.0)
            else:
                if stock > 0:
                    efficiency_score = 0.0
                else:
                    efficiency_score = 100.0

            # Overall Weighted Score
            overall_score = sales_score * 0.40 + rating_score * 0.30 + efficiency_score * 0.30

            if overall_score >= 70.0:
                status = "PERFORMING"
                recommendation = "Pertahankan produksi dan tingkat persediaan saat ini."
            elif overall_score >= 50.0:
                status = "OPTIMIZE"
                recommendation = "Perlu optimasi: tinjau harga, buat promosi ringan, atau perbaiki kualitas/review."
            else:
                status = "RETIRE"
                recommendation = "Kaji ulang / Berpotensi hentikan produksi karena penjualan rendah, rating buruk, atau tidak efisien."

            audits.append({
                "product_id": str(p_id),
                "product_name": p_info["product_name"],
                "current_stock": stock,
                "total_sold_period": sold,
                "avg_rating": round(avg_rating, 2),
                "review_count": count,
                "sales_score": round(sales_score, 2),
                "rating_score": round(rating_score, 2),
                "efficiency_score": round(efficiency_score, 2),
                "overall_score": round(overall_score, 2),
                "status": status,
                "recommendation": recommendation
            })

        # Sort audits by overall_score ascending (worst first, to highlight issues)
        audits.sort(key=lambda x: x["overall_score"])

        result_payload = {
            "store_id": store_id,
            "period_days": period_days,
            "audits": audits
        }

        if redis_client:
            try:
                await redis_client.set(cache_key, json.dumps(result_payload), ex=300)
            except Exception:
                pass

        return result_payload
