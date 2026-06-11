import logging
from typing import Any

from app.mcp.registry import mcp_registry

logger = logging.getLogger(__name__)


class MCPOrchestrator:
    @staticmethod
    async def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Looks up a tool in the global registry and executes it with provided arguments.
        """
        tool = mcp_registry.get_tool(name)
        if not tool:
            logger.error(f"MCP tool not found in registry: {name}")
            return {
                "success": False,
                "error": f"Tool '{name}' is not a registered MCP tool."
            }

        try:
            # Validate input arguments against Pydantic schema
            validated_input = tool.input_schema(**arguments)

            # Execute tool
            logger.info(f"Executing MCP tool '{name}' with arguments: {validated_input}")
            result = await tool.execute(**validated_input.model_dump())
            return {
                "success": True,
                "tool": name,
                "data": result
            }
        except Exception as e:
            logger.error(f"Failed executing MCP tool '{name}': {e}")
            return {
                "success": False,
                "tool": name,
                "error": str(e)
            }
