import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIFactory
from app.modules.chat.constants import DEFAULT_SYSTEM_PROMPT
from app.modules.chat.service.conversation_service import ConversationService
from app.modules.chat.service.memory_service import MemoryService


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_service = ConversationService(db)
        self.memory_service = MemoryService(db)

    async def get_response(self, user_id: uuid.UUID, conversation_id: uuid.UUID, user_message: str) -> str:
        # 1. Fetch conversation history
        conv = await self.conv_service.get_conversation(conversation_id)
        if not conv or conv.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # 2. Save user message to DB
        await self.conv_service.add_message(conversation_id, "user", user_message)

        # 3. Build chat history payload for LLM
        messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
        for msg in conv.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the current message
        messages.append({"role": "user", "content": user_message})

        # 4. Generate LLM response
        llm = AIFactory.get_llm_provider()
        response_content = await llm.generate_chat_response(messages)

        # 5. Save assistant response to DB
        await self.conv_service.add_message(conversation_id, "assistant", response_content)

        return response_content
