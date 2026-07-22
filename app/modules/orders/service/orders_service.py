import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, time

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    OrderChannel,
    OrderStatus,
    PaymentMethod,
    TransactionStatus,
    WalletTransactionCategory,
    WalletType,
)
from app.modules.inventory.models import InventoryBatch, InventoryTransaction
from app.modules.orders.models import Order, OrderItem, OrderItemBatch
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate
from app.modules.products.repository import ProductRepository
from app.modules.transactions.models import Transaction
from app.modules.wallets.service.wallets_service import WalletService


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
                selectinload(Order.store),
                selectinload(Order.transactions),
                selectinload(Order.review),
                selectinload(Order.order_items).selectinload(OrderItem.product),
                selectinload(Order.order_items).selectinload(OrderItem.order_item_variant_options),
                selectinload(Order.order_items).selectinload(OrderItem.order_item_batches).selectinload(OrderItemBatch.inventory_batch),
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
                selectinload(Order.store),
                selectinload(Order.transactions),
                selectinload(Order.review),
                selectinload(Order.order_items).selectinload(OrderItem.product),
                selectinload(Order.order_items).selectinload(OrderItem.order_item_variant_options),
                selectinload(Order.order_items).selectinload(OrderItem.order_item_batches).selectinload(OrderItemBatch.inventory_batch),
            )
        )
        return result.scalars().all()

    async def list_orders_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        store_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> tuple[Sequence[Order], int]:
        from sqlalchemy import func
        query = select(Order)
        
        # Apply options
        query = query.options(
            selectinload(Order.user),
            selectinload(Order.store),
            selectinload(Order.transactions),
            selectinload(Order.review),
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.order_items).selectinload(OrderItem.order_item_variant_options),
            selectinload(Order.order_items).selectinload(OrderItem.order_item_batches).selectinload(OrderItemBatch.inventory_batch),
        )
        
        # Apply store_id filter
        if store_id is not None:
            query = query.where(Order.store_id == store_id)

        # Apply user_id filter
        if user_id is not None:
            query = query.where(Order.user_id == user_id)
            
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


    async def get_available_stock(self, product_id: uuid.UUID, store_id: uuid.UUID) -> int:
        from datetime import UTC, datetime
        now = datetime.now(UTC)

        # Check if ANY inventory batches exist for this product and store
        query_all = select(InventoryBatch).where(
            InventoryBatch.product_id == product_id,
            InventoryBatch.store_id == store_id
        )
        res_all = await self.db.execute(query_all)
        all_batches = res_all.scalars().all()

        if all_batches:
            # If product has inventory batches, available stock is strictly the sum of active non-expired batches
            active_batches = [b for b in all_batches if b.remaining_quantity > 0 and b.expired_at > now]
            return sum(b.remaining_quantity for b in active_batches)

        # Fallback to product.stock ONLY if no inventory batches exist in DB for this product
        product = await self.product_repo.get_by_id(product_id)
        return product.stock if product else 0

    async def create_order(self, user_id: uuid.UUID, schema: OrderCreate) -> Order:
        total_price = 0
        total_discount = 0
        order_items_to_create: list[tuple[OrderItem, uuid.UUID, int]] = [] # (order_item, product_id, quantity)

        # Determine order status
        if schema.status:
            order_status = schema.status
        elif schema.channel == OrderChannel.KASIR:
            order_status = OrderStatus.COMPLETED
        else:
            order_status = OrderStatus.PENDING

        # Validate items, check stock, and calculate prices
        for item in schema.items:
            product = await self.product_repo.get_by_id(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found"
                )

            avail_stock = await self.get_available_stock(product.id, schema.store_id)
            if avail_stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stok tidak mencukupi untuk produk '{product.name}'. Stok tersedia: {avail_stock}, diminta: {item.quantity}"
                )

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
            order_items_to_create.append((order_item, product.id, item.quantity))

        final_price = total_price - total_discount

        # Generate daily code: {weekday_prefix}-{count_today + 1}
        from datetime import UTC, datetime, time
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
            status=order_status,
            channel=schema.channel,
            notes=getattr(schema, "notes", None),
            daily_code=daily_code
        )

        self.db.add(order)
        await self.db.flush()  # Populate order.id

        # Link order items
        for order_item, product_id, qty in order_items_to_create:
            order_item.order_id = order.id
            self.db.add(order_item)

        await self.db.flush()

        # Release user's cart reservations since order is created
        from app.modules.cart.models import CartReservation
        from sqlalchemy import delete
        await self.db.execute(
            delete(CartReservation).where(CartReservation.user_id == user_id)
        )

        # Always deduct stock to secure the inventory batches immediately (Stock Lock)
        await self._deduct_inventory(
            order=order,
            order_items_tuples=order_items_to_create,
            now=now
        )

        # If order is paid, prepared, completed, or KASIR, perform financial logging
        if order_status in [OrderStatus.PAID, OrderStatus.PREPARED, OrderStatus.COMPLETED] or schema.channel == OrderChannel.KASIR:
            await self._process_finance_and_wallet(
                order=order,
                payment_method=schema.payment_method or PaymentMethod.CASH,
                payment_details=schema.payment_details,
                now=now
            )

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

    async def _deduct_inventory(
        self,
        order: Order,
        order_items_tuples: list[tuple[OrderItem, uuid.UUID, int]],
        now: datetime
    ):
        for order_item, product_id, qty in order_items_tuples:
            product = await self.product_repo.get_by_id(product_id)
            if product:
                product.stock = max(0, product.stock - qty)
                self.db.add(product)

            # Deduct stock from active batches (FIFO order)
            batch_query = (
                select(InventoryBatch)
                .where(
                    InventoryBatch.product_id == product_id,
                    InventoryBatch.store_id == order.store_id,
                    InventoryBatch.remaining_quantity > 0,
                )
            )
            batch_res = await self.db.execute(batch_query)
            all_batches = list(batch_res.scalars().all())

            # Filter and sort in Python memory for timezone-safe date comparison
            active_batches = [b for b in all_batches if b.expired_at > now]
            active_batches.sort(key=lambda b: b.expired_at)

            needed = qty
            for b in active_batches:
                if needed <= 0:
                    break
                qty_deduct = min(needed, b.remaining_quantity)
                b.remaining_quantity -= qty_deduct
                self.db.add(b)

                # OrderItemBatch link
                oi_batch = OrderItemBatch(
                    order_item_id=order_item.id,
                    inventory_batch_id=b.id,
                    quantity=qty_deduct
                )
                self.db.add(oi_batch)

                # InventoryTransaction record
                inv_tx = InventoryTransaction(
                    product_id=product_id,
                    store_id=order.store_id,
                    inventory_batch_id=b.id,
                    batch_tag=b.batch_tag,
                    type="sold",
                    quantity=-qty_deduct,
                    reason=f"Penjualan Order #{order.daily_code}",
                    reference=str(order.id)
                )
                self.db.add(inv_tx)

                needed -= qty_deduct

    async def _process_finance_and_wallet(
        self,
        order: Order,
        payment_method: PaymentMethod,
        payment_details: dict | None,
        now: datetime
    ):
        # Financial Transaction & Wallet logging
        platform_fee = 0 if order.channel == OrderChannel.KASIR else int(order.final_price * 0.1)
        net_amount = order.final_price - platform_fee

        transaction_id = uuid.uuid4()
        transaction = Transaction(
            id=transaction_id,
            order_id=order.id,
            store_id=order.store_id,
            gross_amount=order.final_price,
            platform_fee=platform_fee,
            net_amount=net_amount,
            payment_method=payment_method,
            status=TransactionStatus.SUCCESS,
            paid_at=now,
            payment_details=payment_details or {"payment_method": payment_method.value}
        )
        self.db.add(transaction)
        await self.db.flush()

        # If it is online payment (not CASH) and not KASIR, route to OrderEscrow (Kantong Sementara)
        is_online = (payment_method != PaymentMethod.CASH) and (order.channel != OrderChannel.KASIR)

        if is_online:
            from app.modules.orders.models import OrderEscrow
            escrow = OrderEscrow(
                order_id=order.id,
                store_id=order.store_id,
                amount=net_amount,
                status="held"
            )
            self.db.add(escrow)
        else:
            wallet_type = WalletType.OFFLINE if payment_method == PaymentMethod.CASH else WalletType.DIGITAL
            wallet_service = WalletService(self.db)
            await wallet_service.add_funds(
                store_id=order.store_id,
                amount=net_amount,
                wallet_type=wallet_type,
                category=WalletTransactionCategory.CAT_SALES,
                transaction_id=transaction_id,
                note=f"Penjualan Order #{order.daily_code}",
                transaction_date=now
            )

    async def _release_escrow_funds(self, order: Order, now: datetime):
        from app.modules.orders.models import OrderEscrow
        from app.modules.wallets.service.wallets_service import WalletService
        from app.core.enums import WalletType, WalletTransactionCategory
        from sqlalchemy import select

        res = await self.db.execute(
            select(OrderEscrow).where(
                OrderEscrow.order_id == order.id,
                OrderEscrow.status == "held"
            )
        )
        escrow = res.scalar_one_or_none()
        if escrow:
            escrow.status = "released"
            escrow.released_at = now
            self.db.add(escrow)

            # Get the transaction to link the wallet transaction
            tx_id = None
            if order.transactions:
                tx_id = order.transactions[0].id

            # Add to the store's digital wallet
            wallet_service = WalletService(self.db)
            await wallet_service.add_funds(
                store_id=order.store_id,
                amount=escrow.amount,
                wallet_type=WalletType.DIGITAL,
                category=WalletTransactionCategory.CAT_SALES,
                transaction_id=tx_id,
                note=f"Pelepasan Escrow Order #{order.daily_code}",
                transaction_date=now
            )

    async def _refund_escrow_funds(self, order: Order, now: datetime):
        from app.modules.orders.models import OrderEscrow
        from sqlalchemy import select

        res = await self.db.execute(
            select(OrderEscrow).where(
                OrderEscrow.order_id == order.id,
                OrderEscrow.status == "held"
            )
        )
        escrow = res.scalar_one_or_none()
        if escrow:
            escrow.status = "refunded"
            escrow.refunded_at = now
            self.db.add(escrow)

    async def update_order_status(self, order_id: uuid.UUID, new_status: OrderStatus) -> Order:
        from datetime import UTC, datetime
        now = datetime.now(UTC)

        order = await self.get_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        # Check if order has deducted stock batches and if it's moving to PAID / CONFIRMED / PREPARED / COMPLETED
        has_batches = any(len(item.order_item_batches) > 0 for item in order.order_items)
        is_advancing = new_status in [OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PREPARED, OrderStatus.COMPLETED]

        if is_advancing and not order.transactions:
            # Perform finance logging
            pm = PaymentMethod.QRIS
            await self._process_finance_and_wallet(
                order=order,
                payment_method=pm,
                payment_details=None,
                now=now
            )

        if new_status == OrderStatus.COMPLETED:
            await self._release_escrow_funds(order, now)

        elif new_status == OrderStatus.CANCELLED:
            await self._refund_escrow_funds(order, now)
            if has_batches:
                for item in order.order_items:
                    product = await self.product_repo.get_by_id(item.product_id)
                    if product:
                        product.stock += item.quantity
                        self.db.add(product)

                    for oi_batch in item.order_item_batches:
                        if oi_batch.inventory_batch:
                            oi_batch.inventory_batch.remaining_quantity += oi_batch.quantity
                            self.db.add(oi_batch.inventory_batch)

                            inv_tx = InventoryTransaction(
                                product_id=item.product_id,
                                store_id=order.store_id,
                                inventory_batch_id=oi_batch.inventory_batch_id,
                                batch_tag=oi_batch.inventory_batch.batch_tag,
                                type="stock_in",
                                quantity=oi_batch.quantity,
                                reason=f"Pembatalan Order #{order.daily_code}",
                                reference=str(order.id)
                            )
                            self.db.add(inv_tx)

        order.status = new_status
        self.db.add(order)
        await self.db.flush()
        await self.db.commit()

        # Reload updated order
        reloaded = await self.get_order(order.id)
        return reloaded or order
