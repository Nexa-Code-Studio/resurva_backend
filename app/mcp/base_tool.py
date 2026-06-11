from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseMCPTool(ABC):
    name: str
    description: str
    input_schema: type[BaseModel]

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
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
