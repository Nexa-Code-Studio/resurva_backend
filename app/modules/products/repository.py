from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.products.models import Ingredient, Product, ProductIngredient


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: AsyncSession):
        super().__init__(Product, db)


class IngredientRepository(BaseRepository[Ingredient]):
    def __init__(self, db: AsyncSession):
        super().__init__(Ingredient, db)


class ProductIngredientRepository(BaseRepository[ProductIngredient]):
    def __init__(self, db: AsyncSession):
        super().__init__(ProductIngredient, db)
