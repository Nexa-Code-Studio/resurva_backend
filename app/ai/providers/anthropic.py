import httpx

from app.ai.exceptions import ProviderException
from app.ai.interfaces.llm_provider import LLMProvider
from app.core.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-5-sonnet-20241022"
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def generate_response(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.generate_chat_response(messages, system_prompt=system_prompt, **kwargs)

    async def generate_chat_response(self, messages: list[dict], system_prompt: str | None = None, **kwargs) -> str:
        if not self.api_key:
            # Fallback mock for local development and testing
            return f"[MOCK ANTHROPIC Response for messages: {len(messages)} items. Request model: {self.model}]"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Anthropic schema expects system prompt as a root field
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            **kwargs
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
                if response.status_code != 200:
                    raise ProviderException(f"Anthropic error response: {response.text}")
                data = response.json()
                return data["content"][0]["text"]
            except Exception as e:
                if isinstance(e, ProviderException):
                    raise
                raise ProviderException(f"Failed to call Anthropic API: {str(e)}")
