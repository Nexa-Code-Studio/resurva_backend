import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import OrderStatus
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate
from app.modules.products.repository import ProductRepository


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        # Fetch order with eager-loaded relations to serialize correctly
        result = await self.db.execute(
            select(Order)
            .filter(Order.id == order_id)
            .options(
                selectinload(Order.user),
                selectinload(Order.transactions),
                selectinload(Order.order_items).selectinload(OrderItem.product),
                selectinload(Order.order_items).selectinload(OrderItem.order_item_variant_options),
            )
        )
        return result.scalar_one_or_none()

    async def list_orders(self, skip: int = 0, limit: int = 100) -> Sequence[Order]:
        result = await self.db.execute(
            select(Order)
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(Order.user),
                selectinload(Order.transactions),
                selectinload(Order.order_items).selectinload(OrderItem.product),
                selectinload(Order.order_items).selectinload(OrderItem.order_item_variant_options),
            )
        )
        return result.scalars().all()

    async def list_orders_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Order], int]:
        from sqlalchemy import func
        query = select(Order)
        
        # Apply options
        query = query.options(
            selectinload(Order.user),
            selectinload(Order.transactions),
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.order_items).selectinload(OrderItem.order_item_variant_options),
        )
        
        # Apply store_id filter
        if store_id is not None:
            query = query.where(Order.store_id == store_id)
            
        # Apply status filter (comma separated values)
        if status:
            status_list = [s.strip().lower() for s in status.split(",") if s.strip()]
            if status_list:
                query = query.where(Order.status.in_(status_list))
                
        # Sort
        if sort_by and hasattr(Order, sort_by):
            col = getattr(Order, sort_by)
            query = query.order_by(col.desc() if sort_order.lower() == "desc" else col.asc())
        else:
            query = query.order_by(Order.created_at.desc())
            
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_res = await self.db.execute(count_query)
        total = count_res.scalar() or 0
        
        # Offset and limit
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        res = await self.db.execute(query)
        items = res.scalars().all()
        return items, total


    async def create_order(self, user_id: uuid.UUID, schema: OrderCreate) -> Order:
        total_price = 0
        total_discount = 0
        order_items_to_create = []

        # Validate items and deduct stock
        for item in schema.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found"
                )

            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for product '{product.name}'. Available: {product.stock}, requested: {item.quantity}"
                )

            # Deduct stock
            product.stock -= item.quantity
            self.db.add(product)

            # Pricing calculations
            subtotal = product.discounted_price * item.quantity
            item_discount = (product.original_price - product.discounted_price) * item.quantity

            total_price += product.original_price * item.quantity
            total_discount += item_discount

            order_item = OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.discounted_price,
                subtotal=subtotal
            )
            order_items_to_create.append(order_item)

        final_price = total_price - total_discount

        # Generate daily code: {weekday_prefix}-{count_today + 1}
        from datetime import datetime, UTC, time
        now = datetime.now(UTC)
        order_day = now.date()
        weekday = order_day.weekday() # 0 = Monday, 6 = Sunday
        prefix = chr(ord('A') + weekday)

        start_dt = datetime.combine(order_day, time.min).replace(tzinfo=UTC)
        end_dt = datetime.combine(order_day, time.max).replace(tzinfo=UTC)

        from sqlalchemy import func
        count_query = select(func.count(Order.id)).where(
            Order.store_id == schema.store_id,
            Order.created_at >= start_dt,
            Order.created_at <= end_dt
        )
        count_res = await self.db.execute(count_query)
        daily_count = count_res.scalar() or 0
        daily_code = f"{prefix}-{daily_count + 1}"

        # Create main Order
        order = Order(
            user_id=user_id,
            store_id=schema.store_id,
            total_price=total_price,
            total_discount=total_discount,
            final_price=final_price,
            status=OrderStatus.PENDING,
            channel=schema.channel,
            notes=getattr(schema, "notes", None),
            daily_code=daily_code
        )

        self.db.add(order)
        await self.db.flush()  # Populate order.id

        # Link order items to order ID
        for item in order_items_to_create:
            item.order_id = order.id
            self.db.add(item)

        await self.db.flush()
        await self.db.commit()

        # Reload order with selectinload
        reloaded_order = await self.get_order(order.id)
        if not reloaded_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve order after creation"
            )
        return reloaded_order

    async def update_order_status(self, order_id: uuid.UUID, new_status: OrderStatus) -> Order:
        order = await self.get_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        order.status = new_status
        self.db.add(order)
        await self.db.flush()
        return order
