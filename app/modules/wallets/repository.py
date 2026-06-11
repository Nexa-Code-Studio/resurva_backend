from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.wallets.models import Wallet, WalletTransaction


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, db: AsyncSession):
        super().__init__(Wallet, db)


class WalletTransactionRepository(BaseRepository[WalletTransaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(WalletTransaction, db)
