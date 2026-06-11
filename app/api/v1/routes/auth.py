from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.auth.service.auth_service import AuthService
from app.modules.users.schemas import UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    schema: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Register a new user (customer, seller, owner, or admin)."""
    auth_service = AuthService(db)
    return await auth_service.register(schema)


@router.post("/login", response_model=TokenResponse)
async def login(
    schema: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Authenticate user with email/username and password."""
    auth_service = AuthService(db)
    return await auth_service.login(schema)


@router.post("/swagger-login", response_model=TokenResponse, include_in_schema=False)
async def swagger_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session)
):
    """Custom login endpoint for Swagger UI OAuth2 password flow."""
    auth_service = AuthService(db)
    req = LoginRequest(
        username_or_email=form_data.username,
        password=form_data.password
    )
    return await auth_service.login(req)
