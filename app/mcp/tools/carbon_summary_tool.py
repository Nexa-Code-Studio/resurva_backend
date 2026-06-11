from pydantic import BaseModel, Field

from app.mcp.base_tool import BaseMCPTool


class CarbonSummaryInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch carbon savings for")


class CarbonSummaryTool(BaseMCPTool):
    name = "carbon_summary"
    description = "Retrieves total carbon emissions saved (kg CO2e) by preventing food waste at a store."
    input_schema = CarbonSummaryInput

    async def execute(self, store_id: str) -> dict:
        return {
            "store_id": store_id,
            "carbon_saved_kg": 156.45,
            "equivalent_trees_planted": 6.5
        }
