import json
import uuid
import logging
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class SessionService:
    @staticmethod
    def _get_key(conversation_id: uuid.UUID) -> str:
        return f"chat:session:{conversation_id}"

    @classmethod
    async def get_slots(cls, conversation_id: uuid.UUID) -> dict[str, str]:
        """
        Retrieves all currently stored slots for the conversation.
        """
        try:
            client = await get_redis_client()
            key = cls._get_key(conversation_id)
            data = await client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting session slots from Redis: {e}")
        return {}

    @classmethod
    async def set_slots(cls, conversation_id: uuid.UUID, slots: dict[str, str], ttl_seconds: int = 1800) -> None:
        """
        Saves or updates key-value slots in the conversation context.
        """
        try:
            client = await get_redis_client()
            key = cls._get_key(conversation_id)
            existing = await cls.get_slots(conversation_id)
            existing.update(slots)
            # Remove empty values
            existing = {k: v for k, v in existing.items() if v is not None}
            if existing:
                await client.set(key, json.dumps(existing), ex=ttl_seconds)
            else:
                await client.delete(key)
        except Exception as e:
            logger.error(f"Error setting session slots in Redis: {e}")

    @classmethod
    async def clear_session(cls, conversation_id: uuid.UUID) -> None:
        """
        Removes all slots for the conversation.
        """
        try:
            client = await get_redis_client()
            key = cls._get_key(conversation_id)
            await client.delete(key)
        except Exception as e:
            logger.error(f"Error clearing session in Redis: {e}")
