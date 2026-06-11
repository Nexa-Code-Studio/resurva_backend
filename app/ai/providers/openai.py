import httpx

from app.ai.exceptions import ProviderException
from app.ai.interfaces.llm_provider import LLMProvider
from app.core.config import settings


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
        return await self.generate_chat_response(messages, **kwargs)

    async def generate_chat_response(self, messages: list[dict], **kwargs) -> str:
        if not self.api_key:
            # Fallback mock for local development and testing
            return f"[MOCK OPENAI Response for messages: {len(messages)} items. Request model: {self.model}]"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
                if response.status_code != 200:
                    raise ProviderException(f"OpenAI error response: {response.text}")
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                if isinstance(e, ProviderException):
                    raise
                raise ProviderException(f"Failed to call OpenAI API: {str(e)}")
