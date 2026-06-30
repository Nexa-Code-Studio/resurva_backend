from datetime import date
import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.mcp.base_tool import BaseMCPTool
from app.modules.stores.models import Store
from app.modules.summaries.models import MonthlySummary


class BusinessOverviewInput(BaseModel):
    business_id: str = Field(description="UUID of the business to fetch the overview for")
    year: int | None = Field(None, description="Year of the summary. Defaults to current year.")
    month: int | None = Field(None, description="Month (1-12) of the summary. Defaults to current month.")


class BusinessOverviewTool(BaseMCPTool):
    name = "business_overview"
    description = "Retrieves an overview comparing revenue, orders, rating, and carbon metrics across all stores under a business."
    input_schema = BusinessOverviewInput
    # Only Owner and Admin can access this tool
    allowed_roles = [UserRole.OWNER, UserRole.ADMIN]

    async def execute(
        self,
        db: AsyncSession,
        business_id: str,
        year: int | None = None,
        month: int | None = None
    ) -> dict[str, Any]:
        business_uuid = uuid.UUID(business_id)
        now = date.today()
        target_year = year or now.year
        target_month = month or now.month

        q = (
            select(
                Store.name,
                MonthlySummary.total_revenue,
                MonthlySummary.total_orders,
                MonthlySummary.avg_rating,
                MonthlySummary.carbon_saved_kg
            )
            .join(MonthlySummary, MonthlySummary.store_id == Store.id)
            .where(
                Store.business_id == business_uuid,
                MonthlySummary.year == target_year,
                MonthlySummary.month == target_month
            )
        )

        result = await db.execute(q)
        rows = result.all()

        return {
            "business_id": business_id,
            "period": f"{target_year}-{target_month:02d}",
            "stores": [
                {
                    "name": r.name,
                    "revenue": r.total_revenue,
                    "orders": r.total_orders,
                    "avg_rating": round(r.avg_rating, 1) if r.avg_rating else 0.0,
                    "carbon_saved_kg": round(r.carbon_saved_kg, 2) if r.carbon_saved_kg else 0.0
                }
                for r in rows
            ]
        }
