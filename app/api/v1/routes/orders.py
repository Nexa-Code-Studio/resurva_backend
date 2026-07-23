import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService, TokenUser
from app.modules.orders.schemas import OrderCreate, OrderResponse, OrderUpdateStatus
from app.modules.orders.service.orders_service import OrderService
from app.modules.users.models import User
from app.modules.logs.schemas import LogCreate
from app.modules.logs.service import LogSystemService

from app.core.enums import UserRole
from app.core.pagination import PaginatedResponse, PaginationMetadata

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    schema: OrderCreate,
    request: Request,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Place a new marketplace order."""
    service = OrderService(db)
    order = await service.create_order(user_id=current_user.id, schema=schema)
    
    try:
        log_service = LogSystemService(db)
        await log_service.create_log(
            schema=LogCreate(
                platform=request.headers.get("X-Platform", "mobile_client"),
                severity="INFO",
                event=f"Created new order #{order.id} with total amount {order.total_amount}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={"order_id": str(order.id), "total_amount": float(order.total_amount), "store_id": str(order.store_id)}
            ),
            user_id=current_user.id
        )
    except Exception:
        pass
        
    return order


@router.get("/", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    page: int = 1,
    page_size: int = 20,
    store_id: uuid.UUID | None = None,
    status: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List orders."""
    service = OrderService(db)
    
    # Enforce role-based scoping
    user_id_filter = None
    store_id_filter = store_id
    
    if current_user.role == UserRole.CUSTOMER:
        user_id_filter = current_user.id
    elif current_user.role in (UserRole.SELLER, UserRole.OWNER):
        if current_user.store_id:
            store_id_filter = current_user.store_id
            
    items, total = await service.list_orders_paginated(
        page=page,
        page_size=page_size,
        store_id=store_id_filter,
        user_id=user_id_filter,
        status=status,
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


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve details of a single order."""
    service = OrderService(db)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    schema: OrderUpdateStatus,
    request: Request,
    current_user: TokenUser = Depends(AccessContextService.get_token_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update status of an order."""
    service = OrderService(db)
    order = await service.update_order_status(order_id, schema.status)
    
    try:
        log_service = LogSystemService(db)
        platform = "web_merchant"
        if current_user.role == UserRole.ADMIN:
            platform = "web_superadmin"
        elif current_user.role == UserRole.CUSTOMER:
            platform = "mobile_client"
        elif current_user.role == UserRole.OWNER:
            platform = "web_enterprise"
            
        custom_platform = request.headers.get("X-Platform")
        if custom_platform in ["mobile_client", "web_merchant", "web_enterprise", "web_superadmin", "system"]:
            platform = custom_platform

        await log_service.create_log(
            schema=LogCreate(
                platform=platform,
                severity="INFO",
                event=f"Updated status of order #{order.id} to {schema.status.value}",
                user_email=current_user.email,
                ip_address=request.client.host if request.client else None,
                details={"order_id": str(order.id), "new_status": schema.status.value}
            ),
            user_id=current_user.id
        )
    except Exception:
        pass
        
    return order
