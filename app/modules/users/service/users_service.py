import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repository.get_by_email(email)

    async def list_users(self, skip: int = 0, limit: int = 100) -> Sequence[User]:
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def list_users_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[User], int]:
        filters = {}
        if role is not None:
            filters["role"] = role
        return await self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )


    async def create_user(self, schema: UserCreate) -> User:
        # Check duplicate email
        existing_email = await self.repository.get_by_email(schema.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check duplicate username
        existing_username = await self.repository.get_by_username(schema.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Hash password
        data = schema.model_dump()
        data["password"] = get_password_hash(data["password"])

        return await self.repository.create(data)

    async def update_user(self, user_id: uuid.UUID, schema: UserUpdate) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        data = schema.model_dump(exclude_unset=True)
        if "password" in data and data["password"]:
            data["password"] = get_password_hash(data["password"])

        return await self.repository.update(user, data)

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        return await self.repository.delete(user_id)
