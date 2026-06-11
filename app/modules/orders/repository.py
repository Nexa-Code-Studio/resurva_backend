from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.orders.models import Order, OrderDiscount, OrderItem


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: AsyncSession):
        super().__init__(Order, db)


class OrderItemRepository(BaseRepository[OrderItem]):
    def __init__(self, db: AsyncSession):
        super().__init__(OrderItem, db)


class OrderDiscountRepository(BaseRepository[OrderDiscount]):
    def __init__(self, db: AsyncSession):
        super().__init__(OrderDiscount, db)
