from pydantic import BaseModel, Field

from app.mcp.base_tool import BaseMCPTool


class ExpiryAlertInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch expiry alerts for")
    critical_only: bool = Field(False, description="If True, only fetches critically close or already expired items")


class ExpiryAlertTool(BaseMCPTool):
    name = "expiry_alerts"
    description = "Retrieves active warnings and critical warnings for products nearing their expiration dates."
    input_schema = ExpiryAlertInput

    async def execute(self, store_id: str, critical_only: bool = False) -> dict:
        return {
            "store_id": store_id,
            "alerts": [
                {
                    "product_name": "Roti Tawar Gandum",
                    "days_until_expiry": 1,
                    "status": "critical"
                }
            ]
        }
