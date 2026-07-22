import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService, TokenUser
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse, UserCreate, UserUpdate
from app.modules.users.service.users_service import UserService
from app.storage.factory import StorageFactory

from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve current authenticated user profile."""
    service = UserService(db)
    user = await service.get_user(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    schema: UserUpdate,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update current user profile details."""
    service = UserService(db)
    return await service.update_user(current_user.id, schema)


@router.post("/upload-image", status_code=status.HTTP_200_OK)
async def upload_user_avatar(
    file: UploadFile = File(...)
):
    """Upload user avatar photo to storage."""
    content = await file.read()
    storage = StorageFactory.get_storage_provider()
    file_path = await storage.upload_file(
        file_content=content,
        filename=file.filename or "unknown",
        folder="users"
    )
    file_url = storage.get_file_url(file_path)
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "storage_path": file_path,
        "access_url": file_url
    }


@router.get("/me/sustainability")
async def get_my_sustainability_stats(
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve sustainability statistics for the current user."""
    from app.modules.carbon.service.carbon_service import CarbonService
    service = CarbonService(db)
    return await service.get_user_sustainability_stats(current_user.id)


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db_session)
):
    service = UserService(db)
    items, total = await service.list_users_paginated(
        page=page,
        page_size=page_size,
        role=role,
        sort_by=sort_by,
        sort_order=sort_order
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



@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse)
async def create_user(
    schema: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    service = UserService(db)
    return await service.create_user(schema)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    schema: UserUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    service = UserService(db)
    return await service.update_user(user_id, schema)


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    service = UserService(db)
    success = await service.delete_user(user_id)
    return {"ok": success}

