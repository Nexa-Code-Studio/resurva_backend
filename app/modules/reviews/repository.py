from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.reviews.models import Review


class ReviewRepository(BaseRepository[Review]):
    def __init__(self, db: AsyncSession):
        super().__init__(Review, db)
