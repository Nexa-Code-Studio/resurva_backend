import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.security import verify_password
from app.modules.auth.repository import RefreshTokenRepository
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

        access_token = JWTService.generate_access_token(
            user.id,
            role=user.role.value,
            email=user.email,
            username=user.username,
            business_id=user.business_id,
            store_id=user.store_id,
            created_at=user.created_at
        )
        refresh_token = JWTService.generate_refresh_token(user.id)

        # Decode token payload to get expiration timestamp
        payload = security.decode_token(refresh_token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

        # Store refresh token in database
        refresh_token_repo = RefreshTokenRepository(self.db)
        await refresh_token_repo.create({
            "user_id": user.id,
            "token": refresh_token,
            "expires_at": expires_at
        })

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access and refresh tokens using Refresh Token Rotation (RTR)
        with stateful tracking and reuse detection.
        """
        # 1. Verify JWT signature & structure
        user_id_str = JWTService.verify_refresh_token(refresh_token)
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject format"
            )

        # 2. Check token in PostgreSQL database
        refresh_token_repo = RefreshTokenRepository(self.db)
        db_token = await refresh_token_repo.get_by_token(refresh_token)

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or invalid"
            )

        # 3. Check if revoked (Reuse detection)
        if db_token.is_revoked:
            # Revoke all tokens for this user!
            await refresh_token_repo.revoke_all_for_user(user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected. All sessions revoked."
            )

        # 4. Check if expired in DB
        if db_token.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )

        # 5. Revoke current token (RTR)
        db_token.is_revoked = True
        self.db.add(db_token)

        # 6. Generate new access and refresh tokens
        # Fetch user details
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # 6. Generate new access and refresh tokens
        new_access_token = JWTService.generate_access_token(
            user.id,
            role=user.role.value,
            email=user.email,
            username=user.username,
            business_id=user.business_id,
            store_id=user.store_id,
            created_at=user.created_at
        )
        new_refresh_token = JWTService.generate_refresh_token(user.id)

        # Save new refresh token
        payload = security.decode_token(new_refresh_token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        await refresh_token_repo.create({
            "user_id": user.id,
            "token": new_refresh_token,
            "expires_at": expires_at
        })

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user=UserResponse.model_validate(user)
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke the given refresh token on logout."""
        refresh_token_repo = RefreshTokenRepository(self.db)
        db_token = await refresh_token_repo.get_by_token(refresh_token)
        if db_token:
            db_token.is_revoked = True
            self.db.add(db_token)
