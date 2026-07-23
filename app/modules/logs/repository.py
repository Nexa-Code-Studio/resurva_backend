from collections.abc import Sequence
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base_repository import BaseRepository
from app.modules.logs.models import LogSystem


class LogSystemRepository(BaseRepository[LogSystem]):
    def __init__(self, db: AsyncSession):
        super().__init__(LogSystem, db)

    async def get_logs_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        platform: str | None = None,
        severity: str | None = None,
        search: str | None = None
    ) -> tuple[Sequence[LogSystem], int]:
        """Fetch paginated, filtered, and searched system logs."""
        query = select(LogSystem).options(selectinload(LogSystem.user))

        # Filter by platform
        if platform and platform != "all":
            query = query.where(LogSystem.platform == platform)

        # Filter by severity
        if severity and severity != "all":
            query = query.where(LogSystem.severity == severity)

        # Search filter (event or user_email)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    LogSystem.event.ilike(search_pattern),
                    LogSystem.user_email.ilike(search_pattern)
                )
            )

        # Order by created_at desc (newest first)
        query = query.order_by(LogSystem.created_at.desc())

        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        count_res = await self.db.execute(count_query)
        total = count_res.scalar() or 0

        # Apply offset and limit
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Fetch results
        res = await self.db.execute(query)
        items = res.scalars().all()

        return items, total
