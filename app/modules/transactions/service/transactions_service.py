import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transactions.models import Transaction
from app.modules.transactions.repository import TransactionRepository
from app.modules.transactions.schemas import TransactionCreate


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.repository = TransactionRepository(db)

    async def create_transaction(self, schema: TransactionCreate) -> Transaction:
        return await self.repository.create(schema.model_dump())

    async def get_store_transactions(self, store_id: uuid.UUID) -> Sequence[Transaction]:
        result = await self.repository.db.execute(
            select(Transaction).filter(Transaction.store_id == store_id)
        )
        return result.scalars().all()

    async def list_transactions_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Transaction], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

