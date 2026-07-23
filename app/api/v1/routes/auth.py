from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.modules.auth.service.auth_service import AuthService
from app.modules.users.schemas import UserCreate, UserResponse
from app.modules.logs.schemas import LogCreate
from app.modules.logs.service import LogSystemService
from app.modules.auth.service.access_context_service import AccessContextService
from app.core.enums import UserRole

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    schema: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Register a new user (customer, seller, owner, or admin)."""
    auth_service = AuthService(db)
    user = await auth_service.register(schema)
    
    try:
        log_service = LogSystemService(db)
        role = schema.role
        platform = "mobile_client"
        if role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif role == UserRole.SELLER:
            platform = "web_merchant"
        elif role == UserRole.OWNER:
            platform = "web_enterprise"
            
        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Registered new user: {user.username} ({user.email})",
                user_email=user.email,
                ip_address=request.client.host if request.client else None,
                details={"role": user.role.value, "user_id": str(user.id)}
            ),
            user_id=user.id
        )
    except Exception:
        pass
        
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    schema: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Authenticate user with email/username and password."""
    auth_service = AuthService(db)
    try:
        token_res = await auth_service.login(schema)
        
        try:
            log_service = LogSystemService(db)
            role = token_res.user.role
            platform = "mobile_client"
            if role == UserRole.ADMIN:
                platform = "web_superadmin"
            elif role == UserRole.SELLER:
                platform = "web_merchant"
            elif role == UserRole.OWNER:
                platform = "web_enterprise"
                
            custom_platform = request.headers.get("X-Platform")
            if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
                platform = custom_platform

            await log_service.create_log(
                schema=LogCreate(
                    platform=platform,
                    severity="INFO",
                    event=f"User login successful: {token_res.user.username}",
                    user_email=token_res.user.email,
                    ip_address=request.client.host if request.client else None,
                    details={"user_id": str(token_res.user.id), "role": token_res.user.role.value}
                ),
                user_id=token_res.user.id
            )
        except Exception:
            pass
            
        return token_res
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                log_service = LogSystemService(db)
                await log_service.create_log(
                    schema=LogCreate(
                        platform=request.headers.get("X-Platform", "system"),
                        severity="WARNING",
                        event=f"Failed login attempt: {schema.username_or_email}",
                        user_email=schema.username_or_email,
                        ip_address=request.client.host if request.client else None,
                        details={"error": e.detail}
                    )
                )
            except Exception:
                pass
        raise e


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    schema: RefreshRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Refresh access and refresh tokens using Refresh Token Rotation."""
    auth_service = AuthService(db)
    return await auth_service.refresh_tokens(schema.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    schema: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Revoke the refresh token on user logout."""
    user_id = None
    user_email = None
    platform = "system"
    
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            token_user = await AccessContextService.get_token_user(token)
            user_id = token_user.id
            user_email = token_user.email
            
            role = token_user.role
            if role == UserRole.ADMIN:
                platform = "web_superadmin"
            elif role == UserRole.CUSTOMER:
                platform = "mobile_client"
            elif role == UserRole.SELLER:
                platform = "web_merchant"
            elif role == UserRole.OWNER:
                platform = "web_enterprise"
        except Exception:
            pass
            
    custom_platform = request.headers.get("X-Platform")
    if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
        platform = custom_platform

    auth_service = AuthService(db)
    await auth_service.logout(schema.refresh_token)

    try:
        log_service = LogSystemService(db)
        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"User logout successful: {user_email or 'unknown'}",
                user_email=user_email,
                ip_address=request.client.host if request.client else None,
                details={}
            ),
            user_id=user_id
        )
    except Exception:
        pass


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
