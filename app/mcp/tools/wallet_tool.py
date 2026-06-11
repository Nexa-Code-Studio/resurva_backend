from pydantic import BaseModel, Field

from app.mcp.base_tool import BaseMCPTool


class WalletToolInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch wallet information for")


class WalletTool(BaseMCPTool):
    name = "check_wallet"
    description = "Checks the financial wallet balance and recent transaction count for a store."
    input_schema = WalletToolInput

    async def execute(self, store_id: str) -> dict:
        return {
            "store_id": store_id,
            "balance": 2500000,
            "recent_withdrawals_count": 2
        }
