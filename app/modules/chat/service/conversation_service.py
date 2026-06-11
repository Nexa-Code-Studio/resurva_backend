import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.chat.models import ChatMessage, Conversation
from app.modules.chat.repository import ChatMessageRepository, ConversationRepository
from app.modules.chat.schemas import ConversationCreate


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = ChatMessageRepository(db)

    async def create_conversation(self, user_id: uuid.UUID, schema: ConversationCreate) -> Conversation:
        data = schema.model_dump()
        data["user_id"] = user_id
        return await self.conv_repo.create(data)

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .filter(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.messages)
                .selectinload(ChatMessage.tool_calls)
            )
        )
        return result.scalar_one_or_none()


    async def get_user_conversations(self, user_id: uuid.UUID) -> Sequence[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().all()

    async def add_message(self, conversation_id: uuid.UUID, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(msg)

        # Touch conversation timestamp
        conv = await self.conv_repo.get_by_id(conversation_id)
        if conv:
            self.db.add(conv)

        await self.db.flush()
        return msg
