import uuid

from pydantic import BaseModel, Field

from app.mcp.base_tool import BaseMCPTool


class InventoryToolInput(BaseModel):
    product_id: str = Field(description="UUID of the product to check inventory for")
    store_id: str = Field(description="UUID of the store holding the inventory")


class InventoryTool(BaseMCPTool):
    name = "check_inventory"
    description = "Checks the available stock batches and quantities for a product in a store."
    input_schema = InventoryToolInput

    async def execute(self, product_id: str, store_id: str) -> dict:
        return {
            "product_id": product_id,
            "store_id": store_id,
            "batches": [
                {
                    "batch_id": str(uuid.uuid4()),
                    "quantity": 10,
                    "remaining_quantity": 8,
                    "expired_at": "2026-06-12T12:00:00Z"
                }
            ]
        }
