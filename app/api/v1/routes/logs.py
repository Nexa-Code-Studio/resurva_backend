import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService, TokenUser, RoleChecker
from app.modules.logs.schemas import LogCreate, LogResponse
from app.modules.logs.service import LogSystemService
from app.core.enums import UserRole
from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


async def get_optional_token_user(request: Request) -> Optional[TokenUser]:
    """Safely extracts TokenUser from Authorization header if present."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        return await AccessContextService.get_token_user(token)
    except Exception:
        return None


@router.post("/", response_model=LogResponse, status_code=status.HTTP_201_CREATED)
async def create_system_log(
    schema: LogCreate,
    optional_user: Optional[TokenUser] = Depends(get_optional_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Record a new log entry.
    Available to both authenticated and unauthenticated clients.
    If authenticated, user metadata will be automatically associated.
    """
    service = LogSystemService(db)
    
    user_id = optional_user.id if optional_user else None
    
    # If the user is logged in, overwrite user_email from token for accuracy
    if optional_user and optional_user.email:
        schema.user_email = optional_user.email
        
    return await service.create_log(schema, user_id=user_id)


@router.get("/", response_model=PaginatedResponse[LogResponse])
async def list_system_logs(
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    current_user: TokenUser = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve system logs.
    Restricted to superadmin (admin role).
    """
    service = LogSystemService(db)
    items, total = await service.list_logs_paginated(
        page=page,
        page_size=page_size,
        platform=platform,
        severity=severity,
        search=search
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=list(items),
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )
