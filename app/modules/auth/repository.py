import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_repository import BaseRepository
from app.modules.auth.models import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(RefreshToken, db)

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Fetch a refresh token by its string value."""
        result = await self.db.execute(
            select(RefreshToken).filter(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all non-revoked refresh tokens for a specific user."""
        result = await self.db.execute(
            select(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
            self.db.add(token)
        await self.db.flush()
