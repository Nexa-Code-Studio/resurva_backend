from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole


class BaseMCPTool(ABC):
    name: str
    description: str
    input_schema: type[BaseModel]
    allowed_roles: list[UserRole] = [UserRole.OWNER, UserRole.SELLER, UserRole.ADMIN]

    @abstractmethod
    async def execute(self, db: AsyncSession, **kwargs) -> dict[str, Any]:
        """
        Executes the tool with the validated arguments from input_schema.
        Returns a dict payload containing results or execution messages.
        """
        pass

    def get_tool_schema(self) -> dict[str, Any]:
        """
        Generates standard JSON-Schema format for LLM tool binding.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema.model_json_schema()
        }
