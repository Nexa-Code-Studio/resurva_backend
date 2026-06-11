import uuid

from pydantic import BaseModel, Field

from app.mcp.base_tool import BaseMCPTool


class ProductSearchInput(BaseModel):
    query: str = Field(description="Search term matching product name or description")
    store_id: str | None = Field(None, description="Filter products by specific store UUID")
    limit: int = Field(10, description="Maximum number of search results to return")


class ProductSearchTool(BaseMCPTool):
    name = "product_search"
    description = "Searches for food items and products available in the waste marketplace."
    input_schema = ProductSearchInput

    async def execute(self, query: str, store_id: str | None = None, limit: int = 10) -> dict:
        # Mock implementation returning placeholder matches
        # In a complete implementation, this would execute queries via ProductRepository
        return {
            "query": query,
            "results": [
                {
                    "id": str(uuid.uuid4()),
                    "name": f"Surplus {query.capitalize()}",
                    "original_price": 50000,
                    "discounted_price": 20000,
                    "stock": 5,
                    "product_type": "bakery"
                }
            ]
        }
