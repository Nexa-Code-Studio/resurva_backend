import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIFactory


class ChatSummaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summarize_conversation(self, conversation_id: uuid.UUID, messages: list) -> str:
        """
        Summarizes chat messages using the LLM Provider Factory.
        """
        if not messages:
            return "Empty conversation"

        text_content = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        prompt = f"Please summarize the following chat conversation history:\n\n{text_content}"

        try:
            llm = AIFactory.get_llm_provider()
            summary = await llm.generate_response(prompt, system_prompt="You are a summarization bot.")
            return summary
        except Exception:
            return f"Summary fallback: conversation has {len(messages)} messages"

