from app.mcp.orchestrator import MCPOrchestrator
from app.mcp.registry import mcp_registry
from app.mcp.tools.carbon_summary_tool import CarbonSummaryTool
from app.mcp.tools.expiry_alert_tool import ExpiryAlertTool
from app.mcp.tools.inventory_tool import InventoryTool
from app.mcp.tools.product_search_tool import ProductSearchTool
from app.mcp.tools.sales_summary_tool import SalesSummaryTool
from app.mcp.tools.wallet_tool import WalletTool
from app.mcp.tools.top_products_tool import TopProductsTool
from app.mcp.tools.reviews_summary_tool import ReviewsSummaryTool
from app.mcp.tools.business_overview_tool import BusinessOverviewTool
from app.mcp.tools.stock_recommendation_tool import StockRecommendationTool
from app.mcp.tools.product_audit_tool import ProductAuditTool
from app.mcp.tools.web_search_tool import WebSearchAndCrawlTool

# Register all tools automatically
mcp_registry.register_tool(ProductSearchTool())
mcp_registry.register_tool(InventoryTool())
mcp_registry.register_tool(SalesSummaryTool())
mcp_registry.register_tool(CarbonSummaryTool())
mcp_registry.register_tool(ExpiryAlertTool())
mcp_registry.register_tool(WalletTool())
mcp_registry.register_tool(TopProductsTool())
mcp_registry.register_tool(ReviewsSummaryTool())
mcp_registry.register_tool(BusinessOverviewTool())
mcp_registry.register_tool(StockRecommendationTool())
mcp_registry.register_tool(ProductAuditTool())
mcp_registry.register_tool(WebSearchAndCrawlTool())
