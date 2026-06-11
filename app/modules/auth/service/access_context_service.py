import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.db.session import get_db_session
from app.modules.auth.service.jwt_service import JWTService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

# Config oauth2 token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=True)


class AccessContextService:
    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db_session)
    ) -> User:
        """
        FastAPI dependency to extract and validate the current authenticated user.
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


class RoleChecker:
    """
    Dependency to enforce Role-Based Access Control (RBAC).
    Usage: Depends(RoleChecker([UserRole.ADMIN, UserRole.OWNER]))
    """
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(AccessContextService.get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of the roles {[r.value for r in self.allowed_roles]}"
            )
        return current_user
