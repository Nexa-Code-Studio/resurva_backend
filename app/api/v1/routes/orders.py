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
        # Broadcast to SSE subscribers for the store
        from app.core.sse import sse_manager
        serialized_order = OrderResponse.model_validate(order).model_dump(mode="json")
        await sse_manager.broadcast_to_store(
            str(order.store_id),
            {"event": "order_created", "order": serialized_order}
        )
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Failed to broadcast order_created event: {e}")

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


@router.get("/stream")
async def stream_orders(
    store_id: uuid.UUID,
    token: str
):
    """Stream order updates/creations for a store using Server-Sent Events (SSE)."""
    import asyncio
    import json
    from fastapi.responses import StreamingResponse
    from app.modules.auth.service.jwt_service import JWTService
    from app.modules.users.service.users_service import UserService
    from app.core.enums import UserRole
    from app.core.sse import sse_manager
    from app.db.session import SessionLocal

    # Validate token
    try:
        user_id_str = JWTService.verify_token(token)
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        async with SessionLocal() as db:
            user_service = UserService(db)
            user = await user_service.get_user(uuid.UUID(user_id_str))
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            
            # Verify access to store
            if user.role != UserRole.ADMIN:
                if user.role in (UserRole.SELLER, UserRole.OWNER):
                    if str(user.store_id) != str(store_id):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have access to this store"
                        )
                else:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

    # Get subscriber queue
    queue = sse_manager.get_queue(str(store_id))

    async def event_generator():
        try:
            # Yield initial connection confirmation
            yield "data: {\"event\": \"connected\"}\n\n"
            while True:
                try:
                    # Wait for next event or send a ping every 25 seconds
                    data = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            # Cleanup on client disconnect
            sse_manager.remove_queue(str(store_id), queue)
            raise
        except Exception:
            sse_manager.remove_queue(str(store_id), queue)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
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
        # Broadcast to SSE subscribers for the store
        from app.core.sse import sse_manager
        serialized_order = OrderResponse.model_validate(order).model_dump(mode="json")
        await sse_manager.broadcast_to_store(
            str(order.store_id),
            {"event": "order_updated", "order": serialized_order}
        )
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Failed to broadcast order_updated event: {e}")

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
