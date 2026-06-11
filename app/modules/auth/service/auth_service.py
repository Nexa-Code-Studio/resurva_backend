from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.auth.service.jwt_service import JWTService
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserResponse
from app.modules.users.service.users_service import UserService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)
        self.user_repo = UserRepository(db)

    async def register(self, schema: UserCreate) -> UserResponse:
        user = await self.user_service.create_user(schema)
        return UserResponse.model_validate(user)

    async def login(self, schema: LoginRequest) -> TokenResponse:
        # Check if username or email
        if "@" in schema.username_or_email:
            user = await self.user_repo.get_by_email(schema.username_or_email)
        else:
            user = await self.user_repo.get_by_username(schema.username_or_email)

        if not user or not verify_password(schema.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = JWTService.generate_access_token(user.id)
        refresh_token = JWTService.generate_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        )
