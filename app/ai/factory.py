from app.ai.interfaces.llm_provider import LLMProvider
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.deepseek import DeepSeekProvider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import settings


class AIFactory:
    @staticmethod
    def get_llm_provider() -> LLMProvider:
        provider_name = settings.AI_PROVIDER.lower()
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "anthropic":
            return AnthropicProvider()
        elif provider_name == "deepseek":
            return DeepSeekProvider()
        else:
            raise ValueError(f"Unknown AI provider: {settings.AI_PROVIDER}")
