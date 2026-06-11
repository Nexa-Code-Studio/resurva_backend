from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.discounts.models import Discount


class DiscountRepository(BaseRepository[Discount]):
    def __init__(self, db: AsyncSession):
        super().__init__(Discount, db)
