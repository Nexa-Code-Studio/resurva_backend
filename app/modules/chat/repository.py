from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.chat.models import ChatMemory, ChatMessage, Conversation, ToolCall


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Conversation, db)


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db: AsyncSession):
        super().__init__(ChatMessage, db)


class ToolCallRepository(BaseRepository[ToolCall]):
    def __init__(self, db: AsyncSession):
        super().__init__(ToolCall, db)


class ChatMemoryRepository(BaseRepository[ChatMemory]):
    def __init__(self, db: AsyncSession):
        super().__init__(ChatMemory, db)
