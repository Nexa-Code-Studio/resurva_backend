import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import WalletTransactionType
from app.modules.wallets.models import Wallet, WalletTransaction
from app.modules.wallets.repository import WalletRepository, WalletTransactionRepository


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.tx_repo = WalletTransactionRepository(db)

    async def get_wallet_by_store(self, store_id: uuid.UUID) -> Wallet | None:
        result = await self.wallet_repo.db.execute(
            select(Wallet).filter(Wallet.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def add_funds(self, store_id: uuid.UUID, amount: int, transaction_id: uuid.UUID | None = None, note: str | None = None) -> WalletTransaction:
        wallet = await self.get_wallet_by_store(store_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store wallet not found"
            )

        wallet.balance += amount
        self.db.add(wallet)
        await self.db.flush()

        tx = WalletTransaction(
            wallet_id=wallet.id,
            transaction_id=transaction_id,
            type=WalletTransactionType.CREDIT,
            amount=amount,
            balance_after=wallet.balance,
            note=note
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def get_wallet_transactions(self, wallet_id: uuid.UUID) -> Sequence[WalletTransaction]:
        result = await self.tx_repo.db.execute(
            select(WalletTransaction).filter(WalletTransaction.wallet_id == wallet_id)
        )
        return result.scalars().all()

    async def list_wallets_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Wallet], int]:
        filters = {}
        if store_id is not None:
            filters["store_id"] = store_id
        return await self.wallet_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def list_wallet_transactions_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        wallet_id: uuid.UUID | None = None,
        store_id: uuid.UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[WalletTransaction], int]:
        filters = {}
        if wallet_id is not None:
            filters["wallet_id"] = wallet_id
        elif store_id is not None:
            wallet = await self.get_wallet_by_store(store_id)
            if wallet:
                filters["wallet_id"] = wallet.id
            else:
                return [], 0

        return await self.tx_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

