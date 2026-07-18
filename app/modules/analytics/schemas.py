import uuid
from typing import Any
from pydantic import BaseModel, Field


class CategoryBreakdownItem(BaseModel):
    category: str
    count: int
    total: int
    avg: int
    percentage: float


class CashflowDailyItem(BaseModel):
    day: str
    cash_in: int
    cash_out: int


class FinancialAnalyticsResponse(BaseModel):
    net_profit: int
    total_revenue: int
    total_expense: int
    surplus_recovery: int
    cashflow_weekly: list[CashflowDailyItem]
    category_breakdown: list[CategoryBreakdownItem]


class SkuSalesItem(BaseModel):
    sku: str
    product_name: str
    qty_sold: int


class CategoryDistributionItem(BaseModel):
    category: str
    percentage: float
    total_sales: int


class SlowMovingItem(BaseModel):
    product_name: str
    days_in_stock: int
    current_stock: int


class SalesAnalyticsResponse(BaseModel):
    sku_sales: list[SkuSalesItem]
    top_products_qty: list[dict[str, Any]]
    category_sales: list[CategoryDistributionItem]
    slow_moving_items: list[SlowMovingItem]


class ProductStockRecommendation(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    current_stock: int
    avg_daily: float
    safety_stock: int
    rop: int
    target_stock: int
    unit: str
    days_remaining: float
    recommended_restock: int
    status: str  # "warning" | "overstock" | "ok"


class InventoryRecommendationResponse(BaseModel):
    items: list[ProductStockRecommendation]
