import json
import logging

import httpx

from app.ai.exceptions import ProviderException
from app.ai.interfaces.llm_provider import LLMProvider, ChatResponse, ToolCallInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-5-sonnet-20241022"
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def generate_response(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        response = await self.generate_chat_response(messages, system_prompt=system_prompt, **kwargs)
        return response.content or ""

    async def generate_chat_response(self, messages: list[dict], system_prompt: str | None = None, **kwargs) -> ChatResponse:
        if not self.api_key:
            return ChatResponse(
                content=f"[MOCK ANTHROPIC Response for messages: {len(messages)} items. Request model: {self.model}]"
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "max_tokens": 1024,
            **self._build_payload(kwargs)
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=headers, timeout=45.0)
                if response.status_code != 200:
                    err_detail = response.text
                    try:
                        err_json = response.json()
                        if "error" in err_json and "message" in err_json["error"]:
                            err_detail = err_json["error"]["message"]
                    except Exception:
                        pass
                    raise ProviderException(f"Anthropic API Error (HTTP {response.status_code}): {err_detail}")

                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error("Anthropic returned non-JSON response: %s", response.text)
                    raise ProviderException(f"Layanan AI mengembalikan respons tidak valid: {e}")

                return self._parse_response(data)
            except ProviderException:
                raise
            except Exception as e:
                logger.error("Anthropic API call failed: %s", e, exc_info=True)
                raise ProviderException(f"Gagal menghubungi layanan Anthropic ({type(e).__name__}: {str(e)})")

    def _build_payload(self, kwargs: dict) -> dict:
        extra = {}
        if "tools" in kwargs and kwargs["tools"]:
            extra["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t["parameters"],
                }
                for t in kwargs["tools"]
            ]
        for k, v in kwargs.items():
            if k != "tools":
                extra[k] = v
        return extra

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            if msg["role"] == "assistant" and "tool_calls" in msg:
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"])
                    })
                converted.append({"role": "assistant", "content": content})
            elif msg["role"] == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"]
                    }]
                })
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})
        return converted

    def _parse_response(self, data: dict) -> ChatResponse:
        content_text = None
        tool_calls = []
        for block in data.get("content", []):
            if block["type"] == "text":
                content_text = block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCallInfo(
                    id=block["id"],
                    name=block["name"],
                    arguments=block["input"]
                ))
        return ChatResponse(content=content_text, tool_calls=tool_calls)
