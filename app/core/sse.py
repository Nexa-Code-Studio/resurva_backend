import asyncio
from typing import Dict, Set
import logging

logger = logging.getLogger("uvicorn.error")

class SseManager:
    def __init__(self):
        # Maps store_id (str) to a set of active asyncio.Queue objects
        self.active_queues: Dict[str, Set[asyncio.Queue]] = {}

    def get_queue(self, store_id: str) -> asyncio.Queue:
        """Register a new asyncio.Queue for a store_id connection."""
        q = asyncio.Queue()
        if store_id not in self.active_queues:
            self.active_queues[store_id] = set()
        self.active_queues[store_id].add(q)
        logger.info(f"[SseManager] Registered new client queue for store {store_id}. Total active: {len(self.active_queues[store_id])}")
        return q

    def remove_queue(self, store_id: str, q: asyncio.Queue):
        """Remove a client queue when they disconnect."""
        if store_id in self.active_queues:
            self.active_queues[store_id].discard(q)
            if not self.active_queues[store_id]:
                del self.active_queues[store_id]
            logger.info(f"[SseManager] Removed client queue for store {store_id}. Remaining active: {len(self.active_queues.get(store_id, []))}")

    async def broadcast_to_store(self, store_id: str, data: dict):
        """Broadcast event payload to all active client queues registered under store_id."""
        if store_id in self.active_queues:
            queues = list(self.active_queues[store_id])
            logger.info(f"[SseManager] Broadcasting event to {len(queues)} clients for store {store_id}")
            for q in queues:
                try:
                    await q.put(data)
                except Exception as e:
                    logger.error(f"[SseManager] Failed to enqueue event for store {store_id}: {e}")
        else:
            logger.info(f"[SseManager] No active subscribers for store {store_id}. Event discarded.")

sse_manager = SseManager()
