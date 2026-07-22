import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService
from app.modules.cart.schemas import CartReserveRequest, CartReserveResponse, CartReleaseRequest
from app.modules.cart.service.cart_service import CartService
from app.modules.users.models import User

router = APIRouter()


@router.post("/reserve", response_model=CartReserveResponse, status_code=status.HTTP_200_OK)
async def reserve_cart_item(
    schema: CartReserveRequest,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Reserve/lock product stock for user's cart (5 min TTL)."""
    service = CartService(db)
    return await service.reserve_stock(user_id=current_user.id, req=schema)


@router.post("/release", status_code=status.HTTP_200_OK)
async def release_cart_item(
    schema: CartReleaseRequest,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Release reserved stock from user's cart."""
    service = CartService(db)
    return await service.release_stock(user_id=current_user.id, product_id=schema.product_id)
