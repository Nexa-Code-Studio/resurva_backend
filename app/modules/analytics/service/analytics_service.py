import uuid
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.wallets.models import Wallet, WalletTransaction
from app.core.enums import OrderStatus
from app.modules.analytics.schemas import (
    FinancialAnalyticsResponse,
    CategoryBreakdownItem,
    CashflowDailyItem,
    SalesAnalyticsResponse,
    SkuSalesItem,
    CategoryDistributionItem,
    SlowMovingItem,
    InventoryRecommendationResponse,
    ProductStockRecommendation,
)


def get_tx_type_str(t: Any) -> str:
    if hasattr(t.type, "value"):
        return str(t.type.value).lower()
    return str(t.type or "").lower()


def get_tx_category_str(t: Any) -> str:
    if hasattr(t, "category") and t.category is not None:
        if hasattr(t.category, "value"):
            return str(t.category.value)
        return str(t.category)
    if hasattr(t, "note") and t.note:
        return str(t.note)
    return "Lainnya"


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_finance_analytics(
        self, store_id: uuid.UUID, timeframe: str = "weekly", tx_type: str = "in"
    ) -> FinancialAnalyticsResponse:
        # 1. Fetch completed/active orders
        orders_stmt = select(Order).options(
            selectinload(Order.order_items).selectinload(OrderItem.product)
        ).where(
            Order.store_id == store_id,
            Order.status.notin_([OrderStatus.CANCELLED])
        )
        orders_res = await self.db.execute(orders_stmt)
        orders = list(orders_res.scalars().all())

        # 2. Fetch store wallet transactions
        wallet_stmt = select(Wallet).where(Wallet.store_id == store_id)
        wallet_res = await self.db.execute(wallet_stmt)
        wallets = list(wallet_res.scalars().all())
        wallet_ids = [w.id for w in wallets]

        tx_list: list[WalletTransaction] = []
        if wallet_ids:
            tx_stmt = select(WalletTransaction).where(
                WalletTransaction.wallet_id.in_(wallet_ids)
            )
            tx_res = await self.db.execute(tx_stmt)
            tx_list = list(tx_res.scalars().all())

        # Compute exact totals
        orders_revenue = sum(o.final_price for o in orders)
        manual_credit = sum(
            t.amount for t in tx_list 
            if get_tx_type_str(t) in ["credit", "in"] and t.amount > 0
        )
        manual_debit = sum(
            abs(t.amount) for t in tx_list 
            if get_tx_type_str(t) in ["debit", "withdrawal", "out"]
        )

        total_revenue = orders_revenue + manual_credit
        total_expense = manual_debit
        net_profit = total_revenue - total_expense

        # Surplus recovery revenue
        surplus_recovery = sum(
            item.subtotal for o in orders for item in o.order_items 
            if item.product and item.product.product_type == "surplus"
        )

        # Weekly Cashflow (7 days)
        day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        now = datetime.now(UTC)
        cashflow_weekly: list[CashflowDailyItem] = []

        for i in range(6, -1, -1):
            day_date = (now - timedelta(days=i)).date()
            day_orders = [o for o in orders if o.created_at and o.created_at.date() == day_date]
            day_tx = [
                t for t in tx_list 
                if (t.transaction_date and t.transaction_date.date() == day_date) or 
                   (hasattr(t, "created_at") and t.created_at and t.created_at.date() == day_date)
            ]

            day_in = sum(o.final_price for o in day_orders) + sum(
                t.amount for t in day_tx if get_tx_type_str(t) in ["credit", "in"] and t.amount > 0
            )
            day_out = sum(
                abs(t.amount) for t in day_tx if get_tx_type_str(t) in ["debit", "withdrawal", "out"]
            )

            cashflow_weekly.append(CashflowDailyItem(
                day=day_names[day_date.weekday()],
                cash_in=day_in,
                cash_out=day_out
            ))

        # Category Breakdown for Finance Table
        category_map: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "total": 0})

        if tx_type == "in":
            # Populate income categories from actual completed orders
            for o in orders:
                for item in o.order_items:
                    cat = item.product.product_type if item.product else "Penjualan POS"
                    category_map[cat]["count"] += item.quantity
                    category_map[cat]["total"] += item.subtotal
        else:
            # Populate expense categories from actual debit transactions
            for t in tx_list:
                if get_tx_type_str(t) in ["debit", "withdrawal", "out"]:
                    cat = get_tx_category_str(t)
                    category_map[cat]["count"] += 1
                    category_map[cat]["total"] += abs(t.amount)

        grand_total = sum(d["total"] for d in category_map.values())
        category_breakdown: list[CategoryBreakdownItem] = []

        for cat_name, data in category_map.items():
            pct = (data["total"] / grand_total * 100.0) if grand_total > 0 else 0.0
            category_breakdown.append(CategoryBreakdownItem(
                category=cat_name,
                count=data["count"],
                total=data["total"],
                avg=round(data["total"] / max(1, data["count"])),
                percentage=round(pct, 1)
            ))

        category_breakdown.sort(key=lambda x: x.total, reverse=True)

        return FinancialAnalyticsResponse(
            net_profit=net_profit,
            total_revenue=total_revenue,
            total_expense=total_expense,
            surplus_recovery=surplus_recovery,
            cashflow_weekly=cashflow_weekly,
            category_breakdown=category_breakdown
        )

    async def get_sales_analytics(
        self, store_id: uuid.UUID, timeframe: str = "weekly", date_offset: int = 0
    ) -> SalesAnalyticsResponse:
        # Fetch products and order items
        prod_stmt = select(Product).where(Product.store_id == store_id)
        prod_res = await self.db.execute(prod_stmt)
        products = list(prod_res.scalars().all())

        orders_stmt = select(Order).options(
            selectinload(Order.order_items).selectinload(OrderItem.product)
        ).where(
            Order.store_id == store_id,
            Order.status.notin_([OrderStatus.CANCELLED])
        )
        orders_res = await self.db.execute(orders_stmt)
        orders = list(orders_res.scalars().all())

        # Aggregate Sales by SKU / Product
        sku_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"sku": "", "name": "", "qty": 0, "total": 0})
        cat_map: dict[str, int] = defaultdict(int)

        for o in orders:
            for item in o.order_items:
                if item.product:
                    p = item.product
                    sku_code = p.sku or f"SKU-{p.id.hex[:4].upper()}"
                    key = p.id
                    sku_map[key]["sku"] = f"{sku_code} ({p.name})"
                    sku_map[key]["name"] = p.name
                    sku_map[key]["qty"] += item.quantity
                    sku_map[key]["total"] += item.subtotal
                    cat_map[p.product_type] += item.subtotal

        # Sort by Qty Sold
        sorted_by_qty = sorted(sku_map.values(), key=lambda x: x["qty"], reverse=True)

        sku_sales = [
            SkuSalesItem(
                sku=item["sku"],
                product_name=item["name"],
                qty_sold=item["qty"]
            )
            for item in sorted_by_qty
        ]

        top_products_qty = [
            {"name": item["name"], "qty_sold": item["qty"]}
            for item in sorted_by_qty[:5]
        ]

        # Category Sales Distribution Doughnut
        total_cat_sales = sum(cat_map.values())
        category_sales = [
            CategoryDistributionItem(
                category=cat,
                percentage=round((val / total_cat_sales * 100.0) if total_cat_sales > 0 else 0.0, 1),
                total_sales=val
            )
            for cat, val in cat_map.items()
        ]
        category_sales.sort(key=lambda x: x.total_sales, reverse=True)

        # Slow-moving items (Products with lowest turnover rate / longest days in stock)
        slow_moving_items = []
        for p in products:
            qty_sold = sku_map.get(p.id, {}).get("qty", 0)
            days_in_stock = round(p.stock / max(1, qty_sold / 30.0)) if qty_sold > 0 else (14 if p.stock > 0 else 0)
            if p.stock > 0:
                slow_moving_items.append(SlowMovingItem(
                    product_name=p.name,
                    days_in_stock=days_in_stock,
                    current_stock=p.stock
                ))
        slow_moving_items.sort(key=lambda x: x.days_in_stock, reverse=True)
        slow_moving_items = slow_moving_items[:5]

        return SalesAnalyticsResponse(
            sku_sales=sku_sales,
            top_products_qty=top_products_qty,
            category_sales=category_sales,
            slow_moving_items=slow_moving_items
        )

    async def get_inventory_recommendations(
        self, store_id: uuid.UUID
    ) -> InventoryRecommendationResponse:
        # Fetch products
        prod_stmt = select(Product).where(Product.store_id == store_id)
        prod_res = await self.db.execute(prod_stmt)
        products = list(prod_res.scalars().all())

        # Fetch 30-day historical order items
        cutoff_date = datetime.now(UTC) - timedelta(days=30)
        orders_stmt = select(Order).options(
            selectinload(Order.order_items)
        ).where(
            Order.store_id == store_id,
            Order.created_at >= cutoff_date,
            Order.status.notin_([OrderStatus.CANCELLED])
        )
        orders_res = await self.db.execute(orders_stmt)
        recent_orders = list(orders_res.scalars().all())

        # Aggregate daily sales per product
        product_daily_sales: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for o in recent_orders:
            date_str = o.created_at.strftime("%Y-%m-%d") if o.created_at else "2026-06-26"
            for item in o.order_items:
                product_daily_sales[item.product_id][date_str] += item.quantity

        recommendations: list[ProductStockRecommendation] = []

        for p in products:
            daily_dict = product_daily_sales.get(p.id, {})
            total_sold_30d = sum(daily_dict.values())
            avg_daily = round(total_sold_30d / 30.0, 1)
            max_daily = max(list(daily_dict.values()) + [int(avg_daily * 1.5)]) if daily_dict else int(avg_daily * 1.5)

            lead_time = getattr(p, "supplier_lead_time_days", 2) or 2
            max_lead_time = lead_time + 2

            # Safety Stock = (Max Daily * Max Lead Time) - (Avg Daily * Lead Time)
            safety_stock = int(round((max_daily * max_lead_time) - (avg_daily * lead_time)))
            safety_stock = max(0, safety_stock)

            # ROP = (Avg Daily * Lead Time) + Safety Stock
            rop = int(round((avg_daily * lead_time) + safety_stock))
            target_stock = rop + int(round(avg_daily * 7))

            days_remaining = round(p.stock / avg_daily, 1) if avg_daily > 0 else 99.0
            recommended_restock = max(0, target_stock - p.stock)

            status = "ok"
            if p.stock <= rop:
                status = "warning"
            elif target_stock > 0 and p.stock >= target_stock * 1.1:
                status = "overstock"

            recommendations.append(ProductStockRecommendation(
                id=p.id,
                name=p.name,
                category=p.product_type,
                current_stock=p.stock,
                avg_daily=avg_daily,
                safety_stock=safety_stock,
                rop=rop,
                target_stock=target_stock,
                unit="Pcs",
                days_remaining=days_remaining,
                recommended_restock=recommended_restock,
                status=status
            ))

        return InventoryRecommendationResponse(items=recommendations)
