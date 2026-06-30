from typing import Any

from app.core.enums import UserRole
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

    def get_tool_schemas_for_role(self, role: UserRole) -> list[dict[str, Any]]:
        """Return the JSON schemas of registered tools that are allowed for the given role."""
        return [tool.get_tool_schema() for tool in self._tools.values() if role in tool.allowed_roles]


# Global registry instance
mcp_registry = MCPRegistry()
