import uuid
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from typing import Any

from sqlalchemy import select, func, and_, or_, extract


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import RefreshToken
from app.modules.business.models import Business
from app.modules.carbon.models import CarbonLog
from app.modules.chat.models import ChatMemory, ChatMessage, Conversation, ToolCall
from app.modules.discounts.models import Discount
from app.modules.inventory.models import ExpiryAlert, InventoryBatch
from app.modules.orders.models import Order, OrderItem, OrderDiscount, OrderItemBatch
from app.modules.products.models import Product, ProductIngredient, Ingredient
from app.modules.reviews.models import Review
from app.modules.stores.models import Store
from app.modules.summaries.models import DailySummary, MonthlySummary
from app.modules.transactions.models import Transaction
from app.modules.users.models import User
from app.modules.wallets.models import Wallet, WalletTransaction



from app.core.enums import OrderStatus, WalletType
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
    EnterpriseFinanceAnalyticsResponse,
    CashflowMonthlyItem,
    EnterpriseLeaderboardResponse,
    LeaderboardItem,
    SustainabilityAnalyticsResponse,
    EnterpriseWrappedResponse,
    BranchWasteComparisonItem,
    EmissionTrendItem,
    EnterpriseWasteImpactAnalyticsResponse,
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
        # Fetch products preloading inventory_batches
        prod_stmt = select(Product).options(selectinload(Product.inventory_batches)).where(Product.store_id == store_id)
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
        now_time = datetime.now(UTC)

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

            # Dynamic active stock calculation matching list_products_paginated
            if p.inventory_batches:
                active_batches = [
                    b for b in p.inventory_batches
                    if b.expired_at > now_time and b.remaining_quantity > 0
                ]
                avail_stock = sum(b.remaining_quantity for b in active_batches)
            else:
                avail_stock = p.stock

            days_remaining = round(avail_stock / avg_daily, 1) if avg_daily > 0 else 99.0
            recommended_restock = max(0, target_stock - avail_stock)

            status = "ok"
            if avail_stock <= rop:
                status = "warning"
            elif target_stock > 0 and avail_stock >= target_stock * 1.1:
                status = "overstock"

            recommendations.append(ProductStockRecommendation(
                id=p.id,
                name=p.name,
                category=p.product_type,
                current_stock=avail_stock,
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

    async def get_enterprise_finance_analytics(
        self, business_id: uuid.UUID
    ) -> EnterpriseFinanceAnalyticsResponse:
        # 1. Fetch all store IDs for this business
        stores_stmt = select(Store).where(Store.business_id == business_id)
        stores_res = await self.db.execute(stores_stmt)
        stores = list(stores_res.scalars().all())
        store_ids = [s.id for s in stores]

        # 2. Fetch completed/active orders across all stores of the business
        orders: list[Order] = []
        if store_ids:
            orders_stmt = select(Order).where(
                Order.store_id.in_(store_ids),
                Order.status.notin_([OrderStatus.CANCELLED])
            )
            orders_res = await self.db.execute(orders_stmt)
            orders = list(orders_res.scalars().all())

        gmv = sum(o.final_price for o in orders)

        # 3. Fetch wallets: all store wallets + business HQ wallet
        wallets_query = select(Wallet).where(
            or_(Wallet.business_id == business_id, Wallet.store_id.in_(store_ids)) if store_ids else (Wallet.business_id == business_id)
        )
        wallets_res = await self.db.execute(wallets_query)
        wallets = list(wallets_res.scalars().all())
        wallet_ids = [w.id for w in wallets]

        hq_wallet = next((w for w in wallets if w.business_id == business_id and w.type == WalletType.HQ), None)
        hq_wallet_id = hq_wallet.id if hq_wallet else None

        tx_list: list[WalletTransaction] = []
        if wallet_ids:
            tx_stmt = select(WalletTransaction).where(
                WalletTransaction.wallet_id.in_(wallet_ids)
            )
            tx_res = await self.db.execute(tx_stmt)
            tx_list = list(tx_res.scalars().all())

        # Compute metrics
        hq_txs = [t for t in tx_list if t.wallet_id == hq_wallet_id] if hq_wallet_id else []
        store_txs = [t for t in tx_list if t.wallet_id != hq_wallet_id] if hq_wallet_id else tx_list

        hq_expense = sum(
            abs(t.amount) for t in hq_txs
            if get_tx_type_str(t) in ["debit", "withdrawal", "out"]
        )

        store_debits = sum(
            abs(t.amount) for t in store_txs
            if get_tx_type_str(t) in ["debit", "withdrawal", "out"]
        )

        # Combined Profit across branches = Total Store Revenue - Store Debits
        store_revenue = gmv + sum(
            t.amount for t in store_txs
            if get_tx_type_str(t) in ["credit", "in"] and t.amount > 0
        )
        total_combined_profit = store_revenue - store_debits

        # Monthly Cashflow Data (Past 6 Months)
        month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        now = datetime.now(UTC)
        cashflow_monthly: list[CashflowMonthlyItem] = []

        for m_offset in range(5, -1, -1):
            m_date = now - timedelta(days=m_offset * 30)
            target_year = m_date.year
            target_month = m_date.month

            m_orders = [
                o for o in orders
                if o.created_at and o.created_at.year == target_year and o.created_at.month == target_month
            ]
            m_txs = [
                t for t in tx_list
                if t.transaction_date and t.transaction_date.year == target_year and t.transaction_date.month == target_month
            ]

            month_in = sum(o.final_price for o in m_orders) + sum(
                t.amount for t in m_txs if get_tx_type_str(t) in ["credit", "in"] and t.amount > 0
            )
            month_out = sum(
                abs(t.amount) for t in m_txs if get_tx_type_str(t) in ["debit", "withdrawal", "out"]
            )

            cashflow_monthly.append(CashflowMonthlyItem(
                month=month_names[target_month - 1],
                cash_in=month_in,
                cash_out=month_out
            ))

        return EnterpriseFinanceAnalyticsResponse(
            gmv=gmv,
            total_combined_profit=total_combined_profit,
            hq_operational_expense=hq_expense,
            cashflow_monthly=cashflow_monthly
        )

    async def get_enterprise_leaderboard(
        self,
        business_id: uuid.UUID,
        period: str = "Bulan Ini",
        category: str = "Semua Kategori",
        sort_by: str = "revenue"
    ) -> EnterpriseLeaderboardResponse:
        now = datetime.now(UTC)
        if period == "Bulan Lalu":
            first_of_this_month = datetime(now.year, now.month, 1, tzinfo=UTC)
            start_date = (first_of_this_month - timedelta(days=1)).replace(day=1)
            end_date = first_of_this_month - timedelta(microseconds=1)
        elif period == "Tahun Ini":
            start_date = datetime(now.year, 1, 1, tzinfo=UTC)
            end_date = now
        else:  # "Bulan Ini"
            start_date = datetime(now.year, now.month, 1, tzinfo=UTC)
            end_date = now

        # Get stores for business with store_category preloaded
        stores_stmt = select(Store).options(selectinload(Store.store_category)).where(Store.business_id == business_id)
        stores_res = await self.db.execute(stores_stmt)
        stores = list(stores_res.scalars().all())

        if category and category != "Semua Kategori":
            stores = [
                s for s in stores 
                if s.store_category and s.store_category.name.lower() == category.lower()
            ]

        if not stores:
            return EnterpriseLeaderboardResponse(period=period, category_filter=category, items=[])

        store_ids = [s.id for s in stores]

        # Query revenue per store
        rev_stmt = (
            select(Order.store_id, func.sum(Order.final_price))
            .where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status != OrderStatus.CANCELLED,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Order.store_id)
        )
        rev_res = await self.db.execute(rev_stmt)
        rev_map = {row[0]: int(row[1] or 0) for row in rev_res.all()}

        # Query eco impact (co2e) per store
        eco_stmt = (
            select(
                Order.store_id,
                func.sum(CarbonLog.carbon_saved_kg)
            )
            .join(CarbonLog, CarbonLog.order_id == Order.id)
            .where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status != OrderStatus.CANCELLED,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Order.store_id)
        )
        eco_res = await self.db.execute(eco_stmt)
        eco_map = {row[0]: float(row[1] or 0.0) for row in eco_res.all()}

        # Query products sold count per store
        prod_stmt = (
            select(Product.store_id, func.sum(Product.sold))
            .where(Product.store_id.in_(store_ids))
            .group_by(Product.store_id)
        )
        prod_res = await self.db.execute(prod_stmt)
        prod_map = {row[0]: int(row[1] or 0) for row in prod_res.all()}

        items: list[LeaderboardItem] = []
        for s in stores:
            rev = rev_map.get(s.id, 0)
            eco_co2 = eco_map.get(s.id, 0.0)
            meals_sold = prod_map.get(s.id, 0)
            saved_kg = round(meals_sold * 0.5, 1) if meals_sold > 0 else (round(eco_co2 / 5.7, 1) if eco_co2 > 0 else 0.0)
            if eco_co2 == 0.0 and saved_kg > 0:
                eco_co2 = round(saved_kg * 5.7, 1)

            cat_str = s.store_category.name if s.store_category else "F&B"
            items.append(LeaderboardItem(
                rank=0,
                store_id=s.id,
                name=s.name,
                category=cat_str,
                revenue=rev,
                saved_kg=saved_kg,
                co2e=round(eco_co2, 1)
            ))



        # Sort items
        if sort_by == "saved_kg":
            items.sort(key=lambda x: x.saved_kg, reverse=True)
        elif sort_by == "co2e":
            items.sort(key=lambda x: x.co2e, reverse=True)
        else:
            items.sort(key=lambda x: x.revenue, reverse=True)

        # Assign ranks
        for idx, item in enumerate(items):
            item.rank = idx + 1

        return EnterpriseLeaderboardResponse(
            period=period,
            category_filter=category,
            items=items
        )

    async def get_enterprise_sustainability(
        self,
        business_id: uuid.UUID,
        period: str = "6bulan"
    ) -> SustainabilityAnalyticsResponse:
        stores_stmt = select(Store).where(Store.business_id == business_id)
        stores_res = await self.db.execute(stores_stmt)
        stores = list(stores_res.scalars().all())

        if not stores:
            return SustainabilityAnalyticsResponse(
                co2e_total=0.0,
                target_co2e=15000.0,
                progress_percent=0.0,
                trees_equivalent=0,
                km_driven_equivalent=0.0,
                phone_hours_equivalent=0,
                monthly_trend=[]
            )

        store_ids = [s.id for s in stores]

        # Calculate Total CO2e
        co2_stmt = (
            select(func.sum(CarbonLog.carbon_saved_kg))
            .join(Order, CarbonLog.order_id == Order.id)
            .where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status != OrderStatus.CANCELLED
                )
            )
        )
        co2_res = await self.db.execute(co2_stmt)
        co2e_total = float(co2_res.scalar() or 0.0)

        # Fallback if 0 from product sold
        if co2e_total == 0.0:
            prod_stmt = select(func.sum(Product.sold)).where(Product.store_id.in_(store_ids))
            prod_res = await self.db.execute(prod_stmt)
            sold_count = int(prod_res.scalar() or 0)
            co2e_total = round(sold_count * 0.5 * 5.7, 1)

        target_co2e = 15000.0
        progress_percent = min(round((co2e_total / target_co2e) * 100, 1), 100.0) if target_co2e > 0 else 0.0

        trees = round(co2e_total * 0.016)
        km_driven = round(co2e_total * 4.1, 1)
        phone_hours = round(co2e_total * 120)

        # Monthly Trend
        month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]
        now = datetime.now(UTC)

        monthly_trend: list[dict[str, Any]] = []

        if period == "tahun_ini":
            for m in range(1, 13):
                m_stmt = (
                    select(func.sum(CarbonLog.carbon_saved_kg))
                    .join(Order, CarbonLog.order_id == Order.id)
                    .where(
                        and_(
                            Order.store_id.in_(store_ids),
                            Order.status != OrderStatus.CANCELLED,
                            extract('year', Order.created_at) == now.year,
                            extract('month', Order.created_at) == m
                        )
                    )
                )
                m_res = await self.db.execute(m_stmt)
                m_val = float(m_res.scalar() or 0.0)
                monthly_trend.append({"label": month_names[m - 1], "co2e": round(m_val, 1)})
        elif period == "semua":
            for y in range(now.year - 4, now.year + 1):
                y_stmt = (
                    select(func.sum(CarbonLog.carbon_saved_kg))
                    .join(Order, CarbonLog.order_id == Order.id)
                    .where(
                        and_(
                            Order.store_id.in_(store_ids),
                            Order.status != OrderStatus.CANCELLED,
                            extract('year', Order.created_at) == y
                        )
                    )
                )
                y_res = await self.db.execute(y_stmt)
                y_val = float(y_res.scalar() or 0.0)
                monthly_trend.append({"label": str(y), "co2e": round(y_val, 1)})
        else:  # "6bulan"
            for offset in range(5, -1, -1):
                d = now - timedelta(days=offset * 30)
                m_stmt = (
                    select(func.sum(CarbonLog.carbon_saved_kg))
                    .join(Order, CarbonLog.order_id == Order.id)
                    .where(
                        and_(
                            Order.store_id.in_(store_ids),
                            Order.status != OrderStatus.CANCELLED,
                            extract('year', Order.created_at) == d.year,
                            extract('month', Order.created_at) == d.month
                        )
                    )
                )
                m_res = await self.db.execute(m_stmt)
                m_val = float(m_res.scalar() or 0.0)
                monthly_trend.append({"label": month_names[d.month - 1], "co2e": round(m_val, 1)})

        return SustainabilityAnalyticsResponse(
            co2e_total=round(co2e_total, 1),
            target_co2e=target_co2e,
            progress_percent=progress_percent,
            trees_equivalent=trees,
            km_driven_equivalent=km_driven,
            phone_hours_equivalent=phone_hours,
            monthly_trend=monthly_trend
        )

    async def get_enterprise_wrapped(
        self,
        business_id: uuid.UUID,
        year: int = 2024
    ) -> EnterpriseWrappedResponse:
        bus_stmt = select(Business).where(Business.id == business_id)
        bus_res = await self.db.execute(bus_stmt)
        business = bus_res.scalar_one_or_none()
        company_name = business.name if business else "Enterprise Group"

        stores_stmt = select(Store).where(Store.business_id == business_id)
        stores_res = await self.db.execute(stores_stmt)
        stores = list(stores_res.scalars().all())

        if not stores:
            return EnterpriseWrappedResponse(
                company_name=company_name,
                year=year,
                food_waste_saved=0.0,
                cost_efficiency=0.0,
                carbon_reduced=0.0,
                trees_equivalent=0,
                gasoline_equivalent=0.0,
                smartphone_charging_hours=0,
                top_branch="Belum Ada Cabang",
                total_branches=0,
                total_orders=0
            )

        store_ids = [s.id for s in stores]

        orders_stmt = select(Order).where(
            and_(
                Order.store_id.in_(store_ids),
                Order.status != OrderStatus.CANCELLED
            )
        )
        orders_res = await self.db.execute(orders_stmt)
        orders = list(orders_res.scalars().all())

        total_orders = len(orders)

        co2_stmt = (
            select(func.sum(CarbonLog.carbon_saved_kg))
            .join(Order, CarbonLog.order_id == Order.id)
            .where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status != OrderStatus.CANCELLED
                )
            )
        )
        co2_res = await self.db.execute(co2_stmt)
        carbon_reduced = float(co2_res.scalar() or 0.0)

        prod_stmt = select(func.sum(Product.sold)).where(Product.store_id.in_(store_ids))
        prod_res = await self.db.execute(prod_stmt)
        sold_count = int(prod_res.scalar() or 0)

        food_waste_saved = round((sold_count * 0.5) if sold_count > 0 else (total_orders * 0.5), 1)

        if carbon_reduced == 0.0 and food_waste_saved > 0:
            carbon_reduced = round(food_waste_saved * 5.7, 1)

        trees = round(carbon_reduced * 0.016)
        gasoline = round(carbon_reduced * 4.1, 1)
        phone_hours = round(carbon_reduced * 120)

        store_counts: dict[uuid.UUID, int] = {}
        for o in orders:
            store_counts[o.store_id] = store_counts.get(o.store_id, 0) + 1

        top_store_id = max(store_counts, key=store_counts.get) if store_counts else store_ids[0]
        top_store = next((s for s in stores if s.id == top_store_id), stores[0])

        return EnterpriseWrappedResponse(
            company_name=company_name,
            year=year,
            food_waste_saved=food_waste_saved,
            cost_efficiency=12.0,
            carbon_reduced=carbon_reduced,
            trees_equivalent=trees,
            gasoline_equivalent=gasoline,
            smartphone_charging_hours=phone_hours,
            top_branch=top_store.name,
            total_branches=len(stores),
            total_orders=total_orders
        )

    async def get_enterprise_waste_impact_analytics(
        self,
        business_id: uuid.UUID
    ) -> EnterpriseWasteImpactAnalyticsResponse:
        stores_stmt = select(Store).where(Store.business_id == business_id)
        stores_res = await self.db.execute(stores_stmt)
        stores = list(stores_res.scalars().all())

        if not stores:
            return EnterpriseWasteImpactAnalyticsResponse(
                financial_loss_avoided=0,
                financial_loss_avoided_growth=0.0,
                food_saved_kg=0.0,
                portions_saved=0,
                co2e_reduced_kg=0.0,
                branch_comparison=[],
                emission_trend=[]
            )

        store_ids = [s.id for s in stores]

        # 1. Total Financial Loss Avoided
        rev_stmt = (
            select(func.sum(Order.final_price))
            .where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status != OrderStatus.CANCELLED
                )
            )
        )
        rev_res = await self.db.execute(rev_stmt)
        financial_loss_avoided = int(rev_res.scalar() or 0)

        # 2. Total Portions & Food Saved (Kg)
        prod_stmt = select(Product.store_id, func.sum(Product.sold)).where(Product.store_id.in_(store_ids)).group_by(Product.store_id)
        prod_res = await self.db.execute(prod_stmt)
        prod_map = {row[0]: int(row[1] or 0) for row in prod_res.all()}
        portions_saved = sum(prod_map.values())
        food_saved_kg = round(portions_saved * 0.5, 1)

        # 3. Total CO2e Reduced
        co2_stmt = (
            select(func.sum(CarbonLog.carbon_saved_kg))
            .join(Order, CarbonLog.order_id == Order.id)
            .where(
                and_(
                    Order.store_id.in_(store_ids),
                    Order.status != OrderStatus.CANCELLED
                )
            )
        )
        co2_res = await self.db.execute(co2_stmt)
        co2e_reduced_kg = float(co2_res.scalar() or 0.0)
        if co2e_reduced_kg == 0.0 and food_saved_kg > 0:
            co2e_reduced_kg = round(food_saved_kg * 5.7, 1)

        # 4. Wasted Food per Store (from expired InventoryBatch)
        wasted_stmt = (
            select(InventoryBatch.store_id, func.sum(InventoryBatch.remaining_quantity))
            .where(
                and_(
                    InventoryBatch.store_id.in_(store_ids),
                    InventoryBatch.expired_at < datetime.now(UTC)
                )
            )
            .group_by(InventoryBatch.store_id)
        )
        wasted_res = await self.db.execute(wasted_stmt)
        wasted_map = {row[0]: float(row[1] or 0.0) * 0.5 for row in wasted_res.all()}


        branch_comparison: list[BranchWasteComparisonItem] = []
        for s in stores:
            s_portions = prod_map.get(s.id, 0)
            s_saved = round(s_portions * 0.5, 1)
            s_wasted = round(wasted_map.get(s.id, 0.0), 1)
            branch_comparison.append(
                BranchWasteComparisonItem(
                    branch_name=s.name,
                    saved_kg=s_saved,
                    wasted_kg=s_wasted
                )
            )

        # 5. Emission Trend (Past 6 Months)
        month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]
        now = datetime.now(UTC)
        emission_trend: list[EmissionTrendItem] = []

        for offset in range(5, -1, -1):
            d = now - timedelta(days=offset * 30)
            m_stmt = (
                select(func.sum(CarbonLog.carbon_saved_kg))
                .join(Order, CarbonLog.order_id == Order.id)
                .where(
                    and_(
                        Order.store_id.in_(store_ids),
                        Order.status != OrderStatus.CANCELLED,
                        extract('year', Order.created_at) == d.year,
                        extract('month', Order.created_at) == d.month
                    )
                )
            )
            m_res = await self.db.execute(m_stmt)
            m_val = float(m_res.scalar() or 0.0)
            emission_trend.append(
                EmissionTrendItem(
                    month=month_names[d.month - 1],
                    co2e_kg=round(m_val, 1)
                )
            )

        return EnterpriseWasteImpactAnalyticsResponse(
            financial_loss_avoided=financial_loss_avoided,
            financial_loss_avoided_growth=15.0,
            food_saved_kg=food_saved_kg,
            portions_saved=portions_saved,
            co2e_reduced_kg=round(co2e_reduced_kg, 1),
            branch_comparison=branch_comparison,
            emission_trend=emission_trend
        )

    async def get_superadmin_stats(self) -> "SuperadminDashboardStatsResponse":
        from app.modules.verifications.models import PartnerVerification
        from app.core.enums import UserRole, OrderStatus
        from app.modules.analytics.schemas import SuperadminDashboardStatsResponse

        # 1. Total general stats
        # Carbon saved
        carbon_stmt = select(func.sum(CarbonLog.carbon_saved_kg))
        carbon_res = await self.db.execute(carbon_stmt)
        total_co2_saved_kg = float(carbon_res.scalar() or 0.0)

        # Food saved (kg)
        meals_stmt = select(func.sum(OrderItem.quantity)).join(Order, Order.id == OrderItem.order_id).filter(Order.status == OrderStatus.COMPLETED)
        meals_res = await self.db.execute(meals_stmt)
        meals_count = int(meals_res.scalar() or 0)
        total_saved_kg = meals_count * 0.5

        # Completed transactions count
        tx_stmt = select(func.count(Order.id)).filter(Order.status == OrderStatus.COMPLETED)
        tx_res = await self.db.execute(tx_stmt)
        total_transactions = int(tx_res.scalar() or 0)

        # Global GMV
        gmv_stmt = select(func.sum(Order.final_price)).filter(Order.status == OrderStatus.COMPLETED)
        gmv_res = await self.db.execute(gmv_stmt)
        global_gmv = float(gmv_res.scalar() or 0.0)

        # User counts (customers & partners)
        cust_stmt = select(func.count(User.id)).filter(User.role == UserRole.CUSTOMER)
        cust_res = await self.db.execute(cust_stmt)
        total_customers = int(cust_res.scalar() or 0)

        partner_stmt = select(func.count(User.id)).filter(User.role.in_([UserRole.SELLER, UserRole.OWNER]))
        partner_res = await self.db.execute(partner_stmt)
        total_partners = int(partner_res.scalar() or 0)

        # 2. Time-based boundaries
        now = datetime.now(UTC)
        current_month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if now.month == 1:
            last_month_start = datetime(now.year - 1, 12, 1, tzinfo=UTC)
        else:
            last_month_start = datetime(now.year, now.month - 1, 1, tzinfo=UTC)
        last_month_end = current_month_start

        # 3. Monthly growth calculations
        # Surplus Saved difference
        cur_meals_stmt = select(func.sum(OrderItem.quantity)).join(Order, Order.id == OrderItem.order_id).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= current_month_start
        )
        cur_meals_res = await self.db.execute(cur_meals_stmt)
        cur_meals = int(cur_meals_res.scalar() or 0)
        cur_saved_kg = cur_meals * 0.5

        last_meals_stmt = select(func.sum(OrderItem.quantity)).join(Order, Order.id == OrderItem.order_id).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= last_month_start,
            Order.created_at < last_month_end
        )
        last_meals_res = await self.db.execute(last_meals_stmt)
        last_meals = last_meals_res.scalar()
        if last_meals is not None:
            last_saved_kg = int(last_meals) * 0.5
            total_saved_kg_diff = cur_saved_kg - last_saved_kg
        else:
            total_saved_kg_diff = None

        # CO2 saved difference
        cur_co2_stmt = select(func.sum(CarbonLog.carbon_saved_kg)).filter(CarbonLog.created_at >= current_month_start)
        cur_co2_res = await self.db.execute(cur_co2_stmt)
        cur_co2 = float(cur_co2_res.scalar() or 0.0)

        last_co2_stmt = select(func.sum(CarbonLog.carbon_saved_kg)).filter(
            CarbonLog.created_at >= last_month_start,
            CarbonLog.created_at < last_month_end
        )
        last_co2_res = await self.db.execute(last_co2_stmt)
        last_co2 = last_co2_res.scalar()
        if last_co2 is not None:
            total_co2_saved_kg_diff = cur_co2 - float(last_co2)
        else:
            total_co2_saved_kg_diff = None

        # New Customers this month
        new_cust_stmt = select(func.count(User.id)).filter(
            User.role == UserRole.CUSTOMER,
            User.created_at >= current_month_start
        )
        new_cust_res = await self.db.execute(new_cust_stmt)
        total_customers_diff = int(new_cust_res.scalar() or 0)

        # New Partners this month
        new_partner_stmt = select(func.count(User.id)).filter(
            User.role.in_([UserRole.SELLER, UserRole.OWNER]),
            User.created_at >= current_month_start
        )
        new_partner_res = await self.db.execute(new_partner_stmt)
        total_partners_diff = int(new_partner_res.scalar() or 0)

        # 4. Pending verifications
        pending_merchant_stmt = select(func.count(PartnerVerification.id)).filter(
            PartnerVerification.status == "PENDING",
            PartnerVerification.partner_type == "MERCHANT"
        )
        pending_merchant_res = await self.db.execute(pending_merchant_stmt)
        pending_merchant = int(pending_merchant_res.scalar() or 0)

        pending_enterprise_stmt = select(func.count(PartnerVerification.id)).filter(
            PartnerVerification.status == "PENDING",
            PartnerVerification.partner_type == "ENTERPRISE"
        )
        pending_enterprise_res = await self.db.execute(pending_enterprise_stmt)
        pending_enterprise = int(pending_enterprise_res.scalar() or 0)

        return SuperadminDashboardStatsResponse(
            total_saved_kg=round(total_saved_kg, 2),
            total_saved_kg_diff=round(total_saved_kg_diff, 2) if total_saved_kg_diff is not None else None,
            total_co2_saved_kg=round(total_co2_saved_kg, 2),
            total_co2_saved_kg_diff=round(total_co2_saved_kg_diff, 2) if total_co2_saved_kg_diff is not None else None,
            total_transactions=total_transactions,
            total_customers=total_customers,
            total_customers_diff=total_customers_diff,
            total_partners=total_partners,
            total_partners_diff=total_partners_diff,
            global_gmv=round(global_gmv, 2),
            pending_merchant_verifications=pending_merchant,
            pending_enterprise_verifications=pending_enterprise
        )




