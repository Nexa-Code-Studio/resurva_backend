import uuid
from difflib import SequenceMatcher
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.mcp.base_tool import BaseMCPTool
from app.modules.products.models import Product


class ProductSearchInput(BaseModel):
    query: str | None = Field(None, description="Optional search term matching product name or description. If omitted, lists/counts all products.")
    store_id: str | None = Field(None, description="Filter products by specific store UUID")
    limit: int = Field(10, description="Maximum number of search results to return")
    include_out_of_stock: bool = Field(True, description="Whether to include products with zero stock (recommended for sellers/owners)")


class ProductSearchTool(BaseMCPTool):
    name = "product_search"
    description = "Searches or lists food items and products available in a store, including out-of-stock items."
    input_schema = ProductSearchInput
    allowed_roles = [UserRole.OWNER, UserRole.SELLER, UserRole.ADMIN, UserRole.CUSTOMER]

    async def execute(
        self,
        db: AsyncSession,
        query: str | None = None,
        store_id: str | None = None,
        limit: int = 10,
        include_out_of_stock: bool = True
    ) -> dict[str, Any]:
        q = select(Product)
        if not include_out_of_stock:
            q = q.where(Product.stock > 0)
        
        if store_id:
            q = q.where(Product.store_id == uuid.UUID(store_id))

        result = await db.execute(q)
        all_products = result.scalars().all()

        results = []
        query_lower = query.strip().lower() if query else ""

        for p in all_products:
            if not query_lower:
                confidence = 1.0
            else:
                ratio_name = SequenceMatcher(None, query_lower, p.name.lower()).ratio()
                ratio_desc = SequenceMatcher(None, query_lower, p.description.lower()).ratio() if p.description else 0.0
                confidence = max(ratio_name, ratio_desc)

            # Only include if there is a decent confidence match (threshold 0.3)
            if not query_lower or confidence >= 0.3:
                results.append({
                    "id": str(p.id),
                    "name": p.name,
                    "original_price": p.original_price,
                    "discounted_price": p.discounted_price,
                    "stock": p.stock,
                    "product_type": p.product_type.value if p.product_type else "other",
                    "description": p.description,
                    "confidence": round(confidence, 2)
                })

        # Sort results by confidence score descending
        results.sort(key=lambda x: x["confidence"], reverse=True)
        total_matching = len(results)
        results = results[:limit]

        return {
            "query": query,
            "total_count": total_matching,
            "results": results
        }
