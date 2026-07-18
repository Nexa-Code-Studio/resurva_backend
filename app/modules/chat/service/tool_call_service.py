import json
import uuid
import decimal
import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.mcp.orchestrator import MCPOrchestrator
from app.modules.chat.models import ToolCall
from app.modules.chat.repository import ToolCallRepository


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class ToolCallService:
    def __init__(self, db: AsyncSession):
        self.repository = ToolCallRepository(db)

    async def execute_and_log_tool(
        self,
        chat_message_id: uuid.UUID,
        role: UserRole,
        allowed_store_ids: list[str] | set[str],
        tool_name: str,
        arguments: dict
    ) -> dict:
        # Execute tool via MCP
        res = await MCPOrchestrator.execute_tool(
            db=self.repository.db,
            role=role,
            allowed_store_ids=allowed_store_ids,
            name=tool_name,
            arguments=arguments
        )

        # Log to DB
        tool_call = ToolCall(
            chat_message_id=chat_message_id,
            tool_name=tool_name,
            tool_input=json.dumps(arguments, default=json_serial),
            tool_output=json.dumps(res, default=json_serial)
        )
        self.repository.db.add(tool_call)
        await self.repository.db.flush()

        return res
