from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        """
        Sends a single text prompt and returns the generated text response.
        """
        pass

    @abstractmethod
    async def generate_chat_response(self, messages: list[dict], **kwargs) -> str:
        """
        Sends a full messages conversation list and returns the generated message content.
        """
        pass
