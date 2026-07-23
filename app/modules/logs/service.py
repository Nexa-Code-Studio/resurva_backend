import uuid
from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.logs.models import LogSystem
from app.modules.logs.repository import LogSystemRepository
from app.modules.logs.schemas import LogCreate


class LogSystemService:
    def __init__(self, db: AsyncSession):
        self.repository = LogSystemRepository(db)

    async def create_log(self, schema: LogCreate, user_id: uuid.UUID | None = None) -> LogSystem:
        """Create a system log."""
        data = schema.model_dump()
        data["user_id"] = user_id
        return await self.repository.create(data)

    async def list_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        platform: str | None = None,
        severity: str | None = None,
        search: str | None = None
    ) -> tuple[Sequence[LogSystem], int]:
        """Fetch filtered and paginated logs."""
        return await self.repository.get_logs_paginated(
            page=page,
            page_size=page_size,
            platform=platform,
            severity=severity,
            search=search
        )
