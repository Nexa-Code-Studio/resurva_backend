import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import ChatMemory
from app.modules.chat.repository import ChatMemoryRepository


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.repository = ChatMemoryRepository(db)

    async def get_memory(self, user_id: uuid.UUID, key: str) -> str | None:
        result = await self.repository.db.execute(
            select(ChatMemory).filter(ChatMemory.user_id == user_id, ChatMemory.key == key)
        )
        mem = result.scalar_one_or_none()
        return mem.value if mem else None

    async def store_memory(self, user_id: uuid.UUID, key: str, value: str) -> ChatMemory:
        result = await self.repository.db.execute(
            select(ChatMemory).filter(ChatMemory.user_id == user_id, ChatMemory.key == key)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
            self.repository.db.add(existing)
            await self.repository.db.flush()
            return existing
        else:
            return await self.repository.create({
                "user_id": user_id,
                "key": key,
                "value": value
            })
