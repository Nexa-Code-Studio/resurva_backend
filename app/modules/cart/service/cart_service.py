import uuid
from datetime import datetime, UTC, timedelta
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.cart.models import CartReservation
from app.modules.cart.schemas import CartReserveRequest, CartReserveResponse
from app.modules.inventory.models import InventoryBatch
from app.modules.products.models import Product


class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_reservations_for_product(self, product_id: uuid.UUID, exclude_user_id: uuid.UUID | None = None) -> int:
        """Returns total quantity of active reservations for a product by OTHER users."""
        now = datetime.now(UTC)
        query = select(func.coalesce(func.sum(CartReservation.quantity), 0)).where(
            CartReservation.product_id == product_id,
            CartReservation.expires_at > now
        )
        if exclude_user_id:
            query = query.where(CartReservation.user_id != exclude_user_id)
        
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def get_product_total_active_stock(self, product_id: uuid.UUID) -> int:
        """Calculates total gross unexpired batch stock for a product."""
        now = datetime.now(UTC)
        query = select(InventoryBatch).where(
            InventoryBatch.product_id == product_id,
            InventoryBatch.remaining_quantity > 0,
        )
        res = await self.db.execute(query)
        batches = res.scalars().all()
        if batches:
            active_batches = [b for b in batches if b.expired_at > now]
            return sum(b.remaining_quantity for b in active_batches)
        
        # Fallback to product.stock if no inventory batches exist
        prod_res = await self.db.execute(select(Product).where(Product.id == product_id))
        prod = prod_res.scalar_one_or_none()
        return prod.stock if prod else 0

    async def reserve_stock(self, user_id: uuid.UUID, req: CartReserveRequest) -> CartReserveResponse:
        now = datetime.now(UTC)
        
        # Clean expired reservations
        await self.db.execute(
            delete(CartReservation).where(CartReservation.expires_at <= now)
        )

        total_batch_stock = await self.get_product_total_active_stock(req.product_id)
        other_reservations = await self.get_active_reservations_for_product(req.product_id, exclude_user_id=user_id)
        
        net_available = max(0, total_batch_stock - other_reservations)

        if req.quantity <= 0:
            # Release reservation for this user & product
            await self.db.execute(
                delete(CartReservation).where(
                    CartReservation.user_id == user_id,
                    CartReservation.product_id == req.product_id
                )
            )
            await self.db.commit()
            return CartReserveResponse(
                product_id=req.product_id,
                reserved_quantity=0,
                available_stock=net_available,
                expires_at=None
            )

        if req.quantity > net_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stok tidak mencukupi untuk dikunci. Stok tersedia: {net_available}, diminta: {req.quantity}"
            )

        # Check existing reservation for this user
        existing_res = await self.db.execute(
            select(CartReservation).where(
                CartReservation.user_id == user_id,
                CartReservation.product_id == req.product_id
            )
        )
        res_obj = existing_res.scalar_one_or_none()
        expires_at = now + timedelta(seconds=req.duration_seconds)

        if res_obj:
            res_obj.quantity = req.quantity
            res_obj.expires_at = expires_at
            self.db.add(res_obj)
        else:
            res_obj = CartReservation(
                id=uuid.uuid4(),
                user_id=user_id,
                product_id=req.product_id,
                quantity=req.quantity,
                expires_at=expires_at
            )
            self.db.add(res_obj)

        await self.db.commit()

        new_net_available = max(0, net_available - req.quantity)
        return CartReserveResponse(
            product_id=req.product_id,
            reserved_quantity=req.quantity,
            available_stock=new_net_available,
            expires_at=expires_at
        )

    async def release_stock(self, user_id: uuid.UUID, product_id: uuid.UUID | None = None) -> dict:
        now = datetime.now(UTC)
        query = delete(CartReservation).where(CartReservation.user_id == user_id)
        if product_id:
            query = query.where(CartReservation.product_id == product_id)
        
        await self.db.execute(query)
        # Also clean all expired reservations globally
        await self.db.execute(delete(CartReservation).where(CartReservation.expires_at <= now))
        await self.db.commit()
        
        return {"status": "success", "message": "Reservasi keranjang berhasil dirilis."}
