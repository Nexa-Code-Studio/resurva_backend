import uuid
from collections.abc import Sequence
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import WalletTransactionType, WalletType, WalletTransactionCategory, TransactionStatus
from app.modules.wallets.models import Wallet, WalletTransaction, WithdrawalRequest
from app.modules.wallets.repository import WalletRepository, WalletTransactionRepository


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.tx_repo = WalletTransactionRepository(db)

    async def get_wallet_by_store(self, store_id: uuid.UUID, wallet_type: WalletType = WalletType.DIGITAL) -> Wallet | None:
        result = await self.wallet_repo.db.execute(
            select(Wallet).filter(Wallet.store_id == store_id, Wallet.type == wallet_type)
        )
        return result.scalar_one_or_none()

    async def add_funds(
        self,
        store_id: uuid.UUID,
        amount: int,
        wallet_type: WalletType = WalletType.DIGITAL,
        category: WalletTransactionCategory = WalletTransactionCategory.CAT_SALES,
        transaction_id: uuid.UUID | None = None,
        note: str | None = None,
        transaction_date: datetime | None = None
    ) -> WalletTransaction:
        wallet = await self.get_wallet_by_store(store_id, wallet_type)
        if not wallet:
            # Auto-create if missing for robustness
            wallet = Wallet(store_id=store_id, type=wallet_type, balance=0)
            self.db.add(wallet)
            await self.db.flush()

        wallet.balance += amount
        self.db.add(wallet)
        await self.db.flush()

        tx = WalletTransaction(
            wallet_id=wallet.id,
            wallet=wallet,
            transaction_id=transaction_id,
            type=WalletTransactionType.CREDIT,
            category=category,
            amount=amount,
            balance_after=wallet.balance,
            note=note,
            transaction_date=transaction_date or datetime.now()
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def create_manual_transaction(
        self,
        store_id: uuid.UUID,
        wallet_type: WalletType,
        type: WalletTransactionType,
        category: WalletTransactionCategory,
        amount: int,
        date: datetime | None = None,
        notes: str | None = None
    ) -> WalletTransaction:
        wallet = await self.get_wallet_by_store(store_id, wallet_type)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store wallet of type '{wallet_type}' not found"
            )

        if type == WalletTransactionType.CREDIT:
            wallet.balance += amount
        else:
            wallet.balance -= amount

        self.db.add(wallet)
        await self.db.flush()

        tx = WalletTransaction(
            wallet_id=wallet.id,
            wallet=wallet,
            type=type,
            category=category,
            amount=amount,
            balance_after=wallet.balance,
            note=notes,
            transaction_date=date or datetime.now()
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def delete_manual_transaction(self, transaction_id: uuid.UUID) -> None:
        tx = await self.tx_repo.get_by_id(transaction_id)
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        if tx.transaction_id is not None or tx.withdrawal_request_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete automated transaction logs"
            )

        wallet = await self.wallet_repo.get_by_id(tx.wallet_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated wallet not found"
            )

        if tx.type == WalletTransactionType.CREDIT:
            wallet.balance -= tx.amount
        else:
            wallet.balance += tx.amount

        self.db.add(wallet)
        await self.tx_repo.delete(transaction_id)
        await self.db.flush()

    async def submit_withdrawal(
        self,
        store_id: uuid.UUID,
        bank_name: str,
        account_number: str,
        account_holder: str,
        amount: int,
        save_account: bool = False
    ) -> WithdrawalRequest:
        wallet = await self.get_wallet_by_store(store_id, WalletType.DIGITAL)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital wallet not found for the store"
            )

        if wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds in digital wallet"
            )

        # Deduct balance
        wallet.balance -= amount
        self.db.add(wallet)

        # Save bank account info if requested
        if save_account:
            wallet.saved_bank_info = {
                "bankName": bank_name,
                "accountNumber": account_number,
                "accountHolder": account_holder
            }
            self.db.add(wallet)

        await self.db.flush()

        # Create Withdrawal Request
        payout = WithdrawalRequest(
            store_id=store_id,
            bank_name=bank_name,
            account_number=account_number,
            account_holder=account_holder,
            amount=amount,
            status=TransactionStatus.PENDING
        )
        self.db.add(payout)
        await self.db.flush()

        # Create Wallet Transaction
        tx = WalletTransaction(
            wallet_id=wallet.id,
            wallet=wallet,
            withdrawal_request_id=payout.id,
            type=WalletTransactionType.WITHDRAWAL,
            category=WalletTransactionCategory.CAT_WITHDRAWAL,
            amount=amount,
            balance_after=wallet.balance,
            note=f"Withdrawal to {bank_name} ({account_number}) - {account_holder}"
        )
        self.db.add(tx)
        await self.db.flush()

        return payout

    async def cancel_withdrawal(self, withdrawal_id: uuid.UUID) -> WithdrawalRequest:
        result = await self.db.execute(
            select(WithdrawalRequest).filter(WithdrawalRequest.id == withdrawal_id)
        )
        payout = result.scalar_one_or_none()
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Withdrawal request not found"
            )

        if payout.status != TransactionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending withdrawals can be cancelled"
            )

        payout.status = TransactionStatus.FAILED
        self.db.add(payout)

        # Refund the balance to digital wallet
        wallet = await self.get_wallet_by_store(payout.store_id, WalletType.DIGITAL)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digital wallet not found for refund"
            )

        wallet.balance += payout.amount
        self.db.add(wallet)
        await self.db.flush()

        # Delete the associated WalletTransaction
        tx_result = await self.db.execute(
            select(WalletTransaction).filter(WalletTransaction.withdrawal_request_id == withdrawal_id)
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            await self.tx_repo.delete(tx.id)

        await self.db.flush()
        return payout

    async def list_withdrawals(self, store_id: uuid.UUID) -> Sequence[WithdrawalRequest]:
        result = await self.db.execute(
            select(WithdrawalRequest)
            .filter(WithdrawalRequest.store_id == store_id)
            .order_by(WithdrawalRequest.created_at.desc())
        )
        return result.scalars().all()

    async def get_wallet_transactions(self, wallet_id: uuid.UUID) -> Sequence[WalletTransaction]:
        from sqlalchemy.orm import selectinload
        result = await self.tx_repo.db.execute(
            select(WalletTransaction)
            .filter(WalletTransaction.wallet_id == wallet_id)
            .options(selectinload(WalletTransaction.wallet), selectinload(WalletTransaction.transaction))
        )
        return result.scalars().all()

    async def get_store_all_transactions(
        self,
        store_id: uuid.UUID,
        wallet_type: WalletType | None = None
    ) -> Sequence[WalletTransaction]:
        from sqlalchemy.orm import selectinload
        # Fetch transactions across digital/offline wallets for a store
        query = (
            select(WalletTransaction)
            .join(Wallet, Wallet.id == WalletTransaction.wallet_id)
            .filter(Wallet.store_id == store_id)
            .options(selectinload(WalletTransaction.wallet), selectinload(WalletTransaction.transaction))
        )
        if wallet_type:
            query = query.filter(Wallet.type == wallet_type)
        
        query = query.order_by(WalletTransaction.transaction_date.desc())
        result = await self.db.execute(query)
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
        from sqlalchemy.orm import selectinload
        filters = {}
        if wallet_id is not None:
            filters["wallet_id"] = wallet_id
        elif store_id is not None:
            # Note: By default returns digital wallet transactions for backward compatibility
            wallet = await self.get_wallet_by_store(store_id, WalletType.DIGITAL)
            if wallet:
                filters["wallet_id"] = wallet.id
            else:
                return [], 0

        return await self.tx_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            options=[selectinload(WalletTransaction.wallet), selectinload(WalletTransaction.transaction)]
        )
