import uuid
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.base_tool import BaseMCPTool
from app.modules.wallets.models import Wallet, WalletTransaction


class WalletToolInput(BaseModel):
    store_id: str = Field(description="UUID of the store to fetch wallet information for")
    include_transactions: bool = Field(False, description="Whether to include recent transactions")
    transaction_type: str | None = Field(None, description="Optional filter for transaction type: 'credit', 'debit', 'withdrawal'")
    limit: int = Field(10, description="Maximum number of recent transactions to return")


class WalletTool(BaseMCPTool):
    name = "check_wallet"
    description = "Checks the financial wallet balance and recent transaction count for a store."
    input_schema = WalletToolInput

    async def execute(
        self,
        db: AsyncSession,
        store_id: str,
        include_transactions: bool = False,
        transaction_type: str | None = None,
        limit: int = 10
    ) -> dict[str, Any]:
        store_uuid = uuid.UUID(store_id)
        result = await db.execute(
            select(Wallet).where(Wallet.store_id == store_uuid)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            return {
                "store_id": store_id,
                "message": "Wallet belum ada"
            }

        data = {
            "store_id": store_id,
            "balance": wallet.balance,
            "updated_at": wallet.updated_at.isoformat() if wallet.updated_at else None
        }

        if include_transactions:
            from app.modules.transactions.models import Transaction
            from sqlalchemy.orm import selectinload

            q = (
                select(WalletTransaction)
                .outerjoin(Transaction, Transaction.id == WalletTransaction.transaction_id)
                .where(WalletTransaction.wallet_id == wallet.id)
            )
            if transaction_type:
                from app.core.enums import WalletTransactionType
                try:
                    t_type = WalletTransactionType(transaction_type.lower())
                    q = q.where(WalletTransaction.type == t_type)
                except ValueError:
                    return {"error": f"Tipe transaksi '{transaction_type}' tidak valid. Gunakan 'credit', 'debit', atau 'withdrawal'."}
            
            q = q.order_by(WalletTransaction.created_at.desc()).limit(limit)
            q = q.options(selectinload(WalletTransaction.transaction))
            
            txn_result = await db.execute(q)
            txns = txn_result.scalars().all()
            data["recent_transactions"] = [
                {
                    "type": t.type.value,
                    "amount": t.amount,
                    "balance_after": t.balance_after,
                    "note": t.note,
                    "status": t.transaction.status.value if t.transaction else "success",
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in txns
            ]
        return data
