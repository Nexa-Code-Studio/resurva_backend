from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCallInfo:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    content: str | None = None
    tool_calls: list[ToolCallInfo] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        pass

    @abstractmethod
    async def generate_chat_response(self, messages: list[dict], **kwargs) -> ChatResponse:
        pass
