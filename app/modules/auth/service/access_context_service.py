import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.enums import UserRole
from app.db.session import get_db_session
from app.modules.auth.service.jwt_service import JWTService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

# Config oauth2 token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=True)


class TokenUser(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    business_id: uuid.UUID | None = None
    store_id: uuid.UUID | None = None
    created_at: datetime


class AccessContextService:
    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db_session)
    ) -> User:
        """
        FastAPI dependency to extract and validate the current authenticated user.
        Queries the database to return the full SQLAlchemy User model.
        """
        user_id_str = JWTService.verify_token(token)
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token identifier format"
            )

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user not found"
            )
        return user

    @staticmethod
    async def get_token_user(
        token: str = Depends(oauth2_scheme)
    ) -> TokenUser:
        """
        FastAPI dependency to extract and validate user data directly from the JWT claims,
        without performing database queries.
        """
        try:
            payload = security.decode_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token credentials"
            )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type, access token expected"
            )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject"
            )
        try:
            user_id = uuid.UUID(str(sub))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token identifier format"
            )

        # Parse other fields from payload
        try:
            role_str = payload.get("role")
            role = UserRole(role_str) if role_str else UserRole.CUSTOMER
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid role in token"
            )

        biz_id_str = payload.get("business_id")
        biz_id = uuid.UUID(biz_id_str) if biz_id_str else None

        store_id_str = payload.get("store_id")
        store_id = uuid.UUID(store_id_str) if store_id_str else None

        created_at_str = payload.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                created_at = datetime.now(UTC)
        else:
            created_at = datetime.now(UTC)

        return TokenUser(
            id=user_id,
            username=payload.get("username", ""),
            email=payload.get("email", ""),
            role=role,
            business_id=biz_id,
            store_id=store_id,
            created_at=created_at
        )


class RoleChecker:
    """
    Dependency to enforce Role-Based Access Control (RBAC).
    Usage: Depends(RoleChecker([UserRole.ADMIN, UserRole.OWNER]))
    """
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: TokenUser = Depends(AccessContextService.get_token_user)) -> TokenUser:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of the roles {[r.value for r in self.allowed_roles]}"
            )
        return current_user
