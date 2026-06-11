import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.orchestrator import MCPOrchestrator
from app.modules.chat.models import ToolCall
from app.modules.chat.repository import ToolCallRepository


class ToolCallService:
    def __init__(self, db: AsyncSession):
        self.repository = ToolCallRepository(db)

    async def execute_and_log_tool(self, chat_message_id: uuid.UUID, tool_name: str, arguments: dict) -> dict:
        # Execute tool via MCP
        res = await MCPOrchestrator.execute_tool(tool_name, arguments)

        # Log to DB
        tool_call = ToolCall(
            chat_message_id=chat_message_id,
            tool_name=tool_name,
            tool_input=json.dumps(arguments),
            tool_output=json.dumps(res)
        )
        self.repository.db.add(tool_call)
        await self.repository.db.flush()

        return res
