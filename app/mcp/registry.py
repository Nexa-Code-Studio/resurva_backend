from typing import Any

from app.mcp.base_tool import BaseMCPTool


class MCPRegistry:
    def __init__(self):
        self._tools: dict[str, BaseMCPTool] = {}

    def register_tool(self, tool: BaseMCPTool) -> None:
        """Register a new MCP tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseMCPTool | None:
        """Retrieve a registered tool by its unique name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseMCPTool]:
        """List all registered tool instances."""
        return list(self._tools.values())

    def get_all_tool_schemas(self) -> list[dict[str, Any]]:
        """Return the JSON schemas of all registered tools."""
        return [tool.get_tool_schema() for tool in self._tools.values()]


# Global registry instance
mcp_registry = MCPRegistry()
