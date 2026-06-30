import json
import logging

import httpx

from app.ai.exceptions import ProviderException
from app.ai.interfaces.llm_provider import LLMProvider, ChatResponse, ToolCallInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.AI_MODEL_NAME or "gpt-4o"
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def generate_response(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await self.generate_chat_response(messages, **kwargs)
        return response.content or ""

    async def generate_chat_response(self, messages: list[dict], **kwargs) -> ChatResponse:
        if not self.api_key:
            return ChatResponse(
                content=f"[MOCK OPENAI Response for messages: {len(messages)} items. Request model: {self.model}]"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            **self._build_payload(kwargs)
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
                if response.status_code != 200:
                    raise ProviderException(f"OpenAI error response: {response.text}")
                data = response.json()
                return self._parse_response(data["choices"][0]["message"])
            except ProviderException:
                raise
            except Exception as e:
                logger.error("OpenAI API call failed: %s", e, exc_info=True)
                return ChatResponse(
                    content=f"Maaf, terjadi kesalahan saat menghubungi layanan AI. Silakan coba lagi. (Error: {type(e).__name__})"
                )

    def _build_payload(self, kwargs: dict) -> dict:
        extra = {}
        if "tools" in kwargs and kwargs["tools"]:
            extra["tools"] = [
                {"type": "function", "function": t}
                for t in kwargs["tools"]
            ]
        for k, v in kwargs.items():
            if k != "tools":
                extra[k] = v
        return extra

    def _parse_response(self, message: dict) -> ChatResponse:
        content = message.get("content")
        tool_calls_data = message.get("tool_calls")
        tool_calls = []
        if tool_calls_data:
            for tc in tool_calls_data:
                tool_calls.append(ToolCallInfo(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"])
                ))
        return ChatResponse(content=content, tool_calls=tool_calls)
