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


class CashflowMonthlyItem(BaseModel):
    month: str
    cash_in: int
    cash_out: int


class EnterpriseFinanceAnalyticsResponse(BaseModel):
    gmv: int
    total_combined_profit: int
    hq_operational_expense: int
    cashflow_monthly: list[CashflowMonthlyItem]



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


class LeaderboardItem(BaseModel):
    rank: int
    store_id: uuid.UUID
    name: str
    category: str
    revenue: int
    saved_kg: float
    co2e: float


class EnterpriseLeaderboardResponse(BaseModel):
    period: str
    category_filter: str
    items: list[LeaderboardItem]


class SustainabilityAnalyticsResponse(BaseModel):
    co2e_total: float
    target_co2e: float
    progress_percent: float
    trees_equivalent: int
    km_driven_equivalent: float
    phone_hours_equivalent: int
    monthly_trend: list[dict[str, Any]]



class EnterpriseWrappedResponse(BaseModel):
    company_name: str
    year: int
    food_waste_saved: float
    cost_efficiency: float
    carbon_reduced: float
    trees_equivalent: int
    gasoline_equivalent: float
    smartphone_charging_hours: int
    top_branch: str
    total_branches: int
    total_orders: int


class BranchWasteComparisonItem(BaseModel):
    branch_name: str
    saved_kg: float
    wasted_kg: float


class EmissionTrendItem(BaseModel):
    month: str
    co2e_kg: float


class EnterpriseWasteImpactAnalyticsResponse(BaseModel):
    financial_loss_avoided: int
    financial_loss_avoided_growth: float
    food_saved_kg: float
    portions_saved: int
    co2e_reduced_kg: float
    branch_comparison: list[BranchWasteComparisonItem]
    emission_trend: list[EmissionTrendItem]


class SuperadminTrendItem(BaseModel):
    month: str
    saved_kg: float
    co2_saved_kg: float
    transactions: int
    gmv: float


class SuperadminDashboardStatsResponse(BaseModel):
    total_saved_kg: float
    total_saved_kg_diff: float | None = None
    total_co2_saved_kg: float
    total_co2_saved_kg_diff: float | None = None
    total_transactions: int
    total_customers: int
    total_customers_diff: int | None = None
    total_partners: int
    total_partners_diff: int | None = None
    global_gmv: float
    pending_merchant_verifications: int
    pending_enterprise_verifications: int
    trends: list[SuperadminTrendItem]



class AIInsightsResponse(BaseModel):
    sales_stock_optimization: str
    surplus_conversion: str
    customer_sentiment: str


class EnterpriseAIInsightsResponse(BaseModel):
    recommendation: str






