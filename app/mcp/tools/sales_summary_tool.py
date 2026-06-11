from pydantic import BaseModel, Field

from app.mcp.base_tool import BaseMCPTool


class SalesSummaryInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch sales data for")
    period: str = Field("daily", description="Summary period: 'daily' or 'monthly'")


class SalesSummaryTool(BaseMCPTool):
    name = "sales_summary"
    description = "Retrieves sales statistics, revenue summaries, and order counts for a store."
    input_schema = SalesSummaryInput

    async def execute(self, store_id: str, period: str = "daily") -> dict:
        return {
            "store_id": store_id,
            "period": period,
            "total_orders": 45 if period == "daily" else 1200,
            "total_revenue": 900000 if period == "daily" else 24000000,
            "items_sold": 60 if period == "daily" else 1500
        }
