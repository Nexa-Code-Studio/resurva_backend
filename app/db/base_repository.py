from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: Any) -> ModelType | None:
        """Fetch a single record by its primary key."""
        result = await self.db.execute(select(self.model).filter(self.model.id == id))  # type: ignore
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Fetch multiple records with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        options: list[Any] | None = None
    ) -> tuple[Sequence[ModelType], int]:
        """
        Generic helper to fetch paginated and sorted records, optionally filtered.
        Returns a tuple of (items, total_count).
        """
        # Build base query
        query = select(self.model)

        # Apply options (like selectinload)
        if options:
            for opt in options:
                query = query.options(opt)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            col_attr = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(col_attr.desc())
            else:
                query = query.order_by(col_attr.asc())
        elif hasattr(self.model, "created_at"):
            query = query.order_by(getattr(self.model, "created_at").desc())
        elif hasattr(self.model, "id"):
            query = query.order_by(getattr(self.model, "id").asc())

        # Count total matching records using a count subquery
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



    async def create(self, data: dict) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**data)
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def update(self, db_obj: ModelType, data: dict) -> ModelType:
        """Update an existing record."""
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def delete(self, id: Any) -> bool:
        """Delete a record by its primary key."""
        db_obj = await self.get_by_id(id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.flush()
            return True
        return False
