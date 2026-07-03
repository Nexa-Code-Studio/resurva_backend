import logging
import random
import uuid
from datetime import UTC, date, datetime, timedelta
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    DiscountType,
    ExpiryAlertStatus,
    OrderChannel,
    OrderStatus,
    PaymentMethod,
    ProductType,
    TransactionStatus,
    WalletTransactionType,
)
from app.modules.orders.models import Order, OrderDiscount, OrderItem, OrderItemBatch
from app.modules.inventory.models import ExpiryAlert, InventoryBatch
from app.modules.products.models import Product, Ingredient, ProductIngredient
from app.modules.reviews.models import Review
from app.modules.summaries.models import DailySummary, MonthlySummary
from app.modules.transactions.models import Transaction
from app.modules.wallets.models import WalletTransaction
from app.modules.carbon.models import CarbonLog
from app.modules.chat.models import Conversation, ChatMessage, ToolCall, ChatMemory
from app.modules.discounts.models import Discount

logger = logging.getLogger("app.db.seeders.order")

class OrderSeeder:
    @staticmethod
    async def seed(
        session: AsyncSession,
        store_ids: list[uuid.UUID],
        wallet_ids: list[uuid.UUID],
        customer_ids: list[uuid.UUID],
        products: list[Product],
        prod_ing_maps: list[ProductIngredient],
        ingredients_map: dict[str, Ingredient],
        discounts: list[Discount]
    ) -> int:
        """
        Simulates and seeds one year of historical order transactions, FEFO batching,
        reviews, and chatbot memory.
        Returns total orders generated.
        """
        logger.info("Starting historical data generation loop...")
        
        store_products_map = {sid: [] for sid in store_ids}
        for p in products:
            if p.store_id in store_products_map:
                store_products_map[p.store_id].append(p)

        # 1. Compute carbon rates per product
        carbon_rates = {}
        for p in products:
            total_c = 0.0
            mapped = False
            for pi in prod_ing_maps:
                if pi.product_id == p.id:
                    mapped = True
                    for ing_name, ing_obj in ingredients_map.items():
                        if ing_obj.id == pi.ingredient_id:
                            total_c += ing_obj.carbon_per_unit * pi.quantity
                            break
            if not mapped or total_c == 0.0:
                if p.product_type == ProductType.PRODUCE:
                    total_c = 0.45
                elif p.product_type == ProductType.BAKERY:
                    total_c = 0.85
                elif p.product_type == ProductType.READY_TO_EAT:
                    total_c = 1.45
                else:
                    total_c = 0.60
            carbon_rates[p.id] = round(total_c, 4)

        # 2. Seeding timeline
        days_history = 365
        end_date = date.today()
        start_date = end_date - timedelta(days=days_history)

        store_balances = {sid: 0 for sid in store_ids}
        daily_summaries_data = {}
        monthly_summaries_data = {}

        status_choices = [OrderStatus.COMPLETED, OrderStatus.PAID, OrderStatus.CANCELLED, OrderStatus.PENDING]
        status_weights = [0.90, 0.05, 0.03, 0.02]
        payment_choices = [PaymentMethod.QRIS, PaymentMethod.GOPAY, PaymentMethod.OVO, PaymentMethod.CASH, PaymentMethod.TRANSFER]

        def get_product_lifespan(prod):
            return timedelta(hours=prod.expiry_time)

        active_batches = {p.id: [] for p in products}

        orders_chunk = []
        order_items_chunk = []
        order_item_batches_chunk = []
        order_discounts_chunk = []
        carbon_logs_chunk = []
        transactions_chunk = []
        wallet_transactions_chunk = []
        inventory_batches_chunk = []
        expiry_alerts_chunk = []

        product_sales_tracker = {p.id: 0 for p in products}
        total_orders_generated = 0
        current_month = start_date.month
        curr_date = start_date

        local_random = random.Random(42)

        while curr_date <= end_date:
            days_passed = (curr_date - start_date).days
            total_days = max(1, (end_date - start_date).days)
            progress = days_passed / total_days

            min_base = int(60 + (220 - 60) * progress)
            max_base = int(90 + (280 - 90) * progress)
            base_orders = local_random.randint(min_base, max_base)

            weekday = curr_date.weekday()
            if weekday in [4, 5, 6]:
                order_count = int(base_orders * local_random.uniform(1.2, 1.4))
            else:
                order_count = int(base_orders * local_random.uniform(0.8, 1.0))

            for _ in range(order_count):
                if not customer_ids:
                    continue
                cust_id = local_random.choice(customer_ids)
                store_id = local_random.choice(store_ids)
                store_prods = store_products_map.get(store_id, [])
                if not store_prods:
                    continue

                chosen_prods = local_random.sample(store_prods, local_random.randint(1, min(3, len(store_prods))))

                order_time = datetime(
                    curr_date.year, curr_date.month, curr_date.day,
                    local_random.randint(7, 21), local_random.randint(0, 59), local_random.randint(0, 59),
                    tzinfo=UTC
                )

                order_id = uuid.uuid4()
                total_price = 0
                carbon_saved = 0.0

                order_items_to_create = []

                for prod in chosen_prods:
                    qty = local_random.randint(1, 3)
                    subtotal = prod.discounted_price * qty
                    total_price += subtotal
                    carbon_saved += carbon_rates[prod.id] * qty

                    oi_id = uuid.uuid4()
                    order_items_to_create.append((oi_id, prod, qty, subtotal))

                    order_items_chunk.append({
                        "id": oi_id,
                        "order_id": order_id,
                        "product_id": prod.id,
                        "quantity": qty,
                        "unit_price": prod.discounted_price,
                        "subtotal": subtotal
                    })

                    p_batches = active_batches[prod.id]
                    valid_batches = [
                        b for b in p_batches
                        if b["expired_at"] > order_time and b["remaining_quantity"] > 0
                    ]
                    valid_batches.sort(key=lambda x: x["expired_at"])

                    allocated_qty = 0
                    for b in valid_batches:
                        if allocated_qty >= qty:
                            break
                        take = min(qty - allocated_qty, b["remaining_quantity"])
                        b["remaining_quantity"] -= take
                        allocated_qty += take

                        order_item_batches_chunk.append({
                            "id": uuid.uuid4(),
                            "order_item_id": oi_id,
                            "inventory_batch_id": b["id"],
                            "quantity": take
                        })

                    if allocated_qty < qty:
                        shortage = qty - allocated_qty
                        new_batch_id = uuid.uuid4()
                        batch_qty = shortage + local_random.randint(30, 80)
                        expired_at = order_time + get_product_lifespan(prod)
                        avail_from = order_time - timedelta(hours=local_random.randint(1, 4))

                        new_batch = {
                            "id": new_batch_id,
                            "product_id": prod.id,
                            "store_id": store_id,
                            "quantity": batch_qty,
                            "remaining_quantity": batch_qty - shortage,
                            "expired_at": expired_at,
                            "available_from": avail_from
                        }
                        active_batches[prod.id].append(new_batch)

                        inventory_batches_chunk.append({
                            "id": new_batch_id,
                            "product_id": prod.id,
                            "store_id": store_id,
                            "quantity": batch_qty,
                            "remaining_quantity": batch_qty,
                            "expired_at": expired_at,
                            "available_from": avail_from,
                            "created_at": avail_from
                        })

                        order_item_batches_chunk.append({
                            "id": uuid.uuid4(),
                            "order_item_id": oi_id,
                            "inventory_batch_id": new_batch_id,
                            "quantity": shortage
                        })

                total_discount = 0
                disc_applied = None
                if local_random.random() < 0.2:
                    for d in discounts:
                        if d.store_id == store_id:
                            disc_applied = d
                            break
                    if disc_applied:
                        if disc_applied.type == DiscountType.PERCENTAGE:
                            total_discount = int(total_price * disc_applied.value / 100)
                        else:
                            total_discount = disc_applied.value
                        total_discount = min(total_discount, total_price)

                final_price = total_price - total_discount
                status = local_random.choices(status_choices, weights=status_weights, k=1)[0]
                channel = OrderChannel.MARKETPLACE if local_random.random() < 0.85 else OrderChannel.KASIR
                pm = local_random.choice(payment_choices)

                orders_chunk.append({
                    "id": order_id,
                    "user_id": cust_id,
                    "store_id": store_id,
                    "total_price": total_price,
                    "total_discount": total_discount,
                    "final_price": final_price,
                    "status": status,
                    "channel": channel,
                    "created_at": order_time
                })

                if disc_applied and total_discount > 0:
                    order_discounts_chunk.append({
                        "id": uuid.uuid4(),
                        "order_id": order_id,
                        "discount_id": disc_applied.id,
                        "discount_amount": total_discount
                    })

                carbon_logs_chunk.append({
                    "id": uuid.uuid4(),
                    "order_id": order_id,
                    "user_id": cust_id,
                    "carbon_saved_kg": round(carbon_saved, 2),
                    "created_at": order_time
                })

                t_id = uuid.uuid4()
                t_status = TransactionStatus.PENDING
                if status == OrderStatus.COMPLETED:
                    t_status = TransactionStatus.SUCCESS
                elif status == OrderStatus.CANCELLED:
                    t_status = TransactionStatus.FAILED

                platform_fee = int(final_price * 0.1)
                net_amount = final_price - platform_fee

                transactions_chunk.append({
                    "id": t_id,
                    "order_id": order_id,
                    "store_id": store_id,
                    "gross_amount": final_price,
                    "platform_fee": platform_fee,
                    "net_amount": net_amount,
                    "payment_method": pm,
                    "status": t_status,
                    "paid_at": order_time if t_status == TransactionStatus.SUCCESS else None,
                    "created_at": order_time
                })

                if t_status == TransactionStatus.SUCCESS:
                    store_balances[store_id] += net_amount
                    store_idx = store_ids.index(store_id)
                    wallet_id = wallet_ids[store_idx]

                    wallet_transactions_chunk.append({
                        "id": uuid.uuid4(),
                        "wallet_id": wallet_id,
                        "transaction_id": t_id,
                        "type": WalletTransactionType.CREDIT,
                        "amount": net_amount,
                        "balance_after": store_balances[store_id],
                        "note": f"Kredit Penjualan Order #{str(order_id)[:8].upper()}",
                        "created_at": order_time
                    })

                    for _, p_obj, item_qty, _ in order_items_to_create:
                        product_sales_tracker[p_obj.id] += item_qty

                    o_date = curr_date
                    day_key = (store_id, o_date)
                    if day_key not in daily_summaries_data:
                        daily_summaries_data[day_key] = {
                            "total_orders": 0, "total_revenue": 0, "total_discount_given": 0,
                            "items_sold": 0, "carbon_saved_kg": 0.0
                        }
                    daily_summaries_data[day_key]["total_orders"] += 1
                    daily_summaries_data[day_key]["total_revenue"] += net_amount
                    daily_summaries_data[day_key]["total_discount_given"] += total_discount
                    daily_summaries_data[day_key]["items_sold"] += len(chosen_prods)
                    daily_summaries_data[day_key]["carbon_saved_kg"] += carbon_saved

                    month_key = (store_id, curr_date.year, curr_date.month)
                    if month_key not in monthly_summaries_data:
                        monthly_summaries_data[month_key] = {
                            "total_orders": 0, "total_revenue": 0, "total_discount_given": 0,
                            "carbon_saved_kg": 0.0, "customers": set()
                        }
                    monthly_summaries_data[month_key]["total_orders"] += 1
                    monthly_summaries_data[month_key]["total_revenue"] += net_amount
                    monthly_summaries_data[month_key]["total_discount_given"] += total_discount
                    monthly_summaries_data[month_key]["carbon_saved_kg"] += carbon_saved
                    monthly_summaries_data[month_key]["customers"].add(cust_id)

                total_orders_generated += 1

            for p_id, p_batches in active_batches.items():
                expired_list = []
                for b in p_batches:
                    if b["expired_at"] <= datetime(curr_date.year, curr_date.month, curr_date.day, 23, 59, 59, tzinfo=UTC):
                        expired_list.append(b)
                        if b["remaining_quantity"] > 0:
                            expiry_alerts_chunk.append({
                                "id": uuid.uuid4(),
                                "product_id": b["product_id"],
                                "store_id": b["store_id"],
                                "days_until_expiry": -1,
                                "status": ExpiryAlertStatus.EXPIRED,
                                "alerted_at": b["expired_at"]
                            })
                for eb in expired_list:
                    p_batches.remove(eb)

            next_day = curr_date + timedelta(days=1)
            if next_day.month != current_month or next_day > end_date:
                logger.info(f"Inserting monthly chunk {current_month}/{curr_date.year}... (Generated {total_orders_generated} orders total)")

                if inventory_batches_chunk:
                    await session.execute(insert(InventoryBatch), inventory_batches_chunk)
                    inventory_batches_chunk.clear()
                if orders_chunk:
                    await session.execute(insert(Order), orders_chunk)
                    orders_chunk.clear()
                if order_items_chunk:
                    await session.execute(insert(OrderItem), order_items_chunk)
                    order_items_chunk.clear()
                if order_item_batches_chunk:
                    await session.execute(insert(OrderItemBatch), order_item_batches_chunk)
                    order_item_batches_chunk.clear()
                if order_discounts_chunk:
                    await session.execute(insert(OrderDiscount), order_discounts_chunk)
                    order_discounts_chunk.clear()
                if carbon_logs_chunk:
                    await session.execute(insert(CarbonLog), carbon_logs_chunk)
                    carbon_logs_chunk.clear()
                if transactions_chunk:
                    await session.execute(insert(Transaction), transactions_chunk)
                    transactions_chunk.clear()
                if wallet_transactions_chunk:
                    await session.execute(insert(WalletTransaction), wallet_transactions_chunk)
                    wallet_transactions_chunk.clear()
                if expiry_alerts_chunk:
                    await session.execute(insert(ExpiryAlert), expiry_alerts_chunk)
                    expiry_alerts_chunk.clear()

                await session.commit()
                current_month = next_day.month

            curr_date = next_day

        logger.info("All orders and transactions generated. Writing summaries & reviews...")

        # 3. Sync balances & stock numbers
        for s_id, final_bal in store_balances.items():
            store_idx = store_ids.index(s_id)
            w_id = wallet_ids[store_idx]
            await session.execute(
                text("UPDATE wallets SET balance = :bal, updated_at = :now WHERE id = :wid"),
                {"bal": final_bal, "now": datetime.now(UTC), "wid": w_id}
            )

        for p in products:
            remaining_stock = sum(b["remaining_quantity"] for b in active_batches[p.id])
            sold_qty = product_sales_tracker[p.id]
            await session.execute(
                text("UPDATE products SET stock = :st, sold = :sold WHERE id = :pid"),
                {"st": remaining_stock, "sold": sold_qty, "pid": p.id}
            )

        for p_id, p_batches in active_batches.items():
            for b in p_batches:
                await session.execute(
                    text("UPDATE inventory_batches SET remaining_quantity = :rq WHERE id = :bid"),
                    {"rq": b["remaining_quantity"], "bid": b["id"]}
                )
        await session.commit()

        # 4. Insert Summaries
        daily_summary_list = []
        for (st_id, s_date), s_val in daily_summaries_data.items():
            daily_summary_list.append({
                "id": uuid.uuid4(),
                "store_id": st_id,
                "summary_date": s_date,
                "total_orders": s_val["total_orders"],
                "total_revenue": s_val["total_revenue"],
                "total_discount_given": s_val["total_discount_given"],
                "items_sold": s_val["items_sold"],
                "carbon_saved_kg": round(s_val["carbon_saved_kg"], 2),
                "expiry_alerts_count": local_random.randint(1, 4),
                "created_at": datetime.combine(s_date, datetime.min.time(), tzinfo=UTC)
            })

        for i in range(0, len(daily_summary_list), 5000):
            await session.execute(insert(DailySummary), daily_summary_list[i:i + 5000])

        monthly_summary_list = []
        for (st_id, yr, mn), m_val in monthly_summaries_data.items():
            # Dynamic rating lookup — find store index, fallback to 4.5
            if st_id in store_ids:
                store_idx = store_ids.index(st_id)
                default_ratings = [4.8, 4.5, 4.6]
                st_rating = default_ratings[store_idx] if store_idx < len(default_ratings) else 4.5
            else:
                st_rating = 4.5
            monthly_summary_list.append({
                "id": uuid.uuid4(),
                "store_id": st_id,
                "year": yr,
                "month": mn,
                "total_orders": m_val["total_orders"],
                "total_revenue": m_val["total_revenue"],
                "total_discount_given": m_val["total_discount_given"],
                "new_customers": len(m_val["customers"]),
                "carbon_saved_kg": round(m_val["carbon_saved_kg"], 2),
                "avg_rating": st_rating,
                "created_at": datetime(yr, mn, 1, 0, 0, 0, tzinfo=UTC)
            })
        if monthly_summary_list:
            await session.execute(insert(MonthlySummary), monthly_summary_list)

        await session.commit()

        # 5. Seed Reviews
        reviews = []
        for p in products:
            if not customer_ids:
                continue
            rev_custs = local_random.sample(customer_ids, local_random.randint(1, 2))
            for c_id in rev_custs:
                rating = local_random.randint(3, 5)
                desc = "Sangat direkomendasikan!" if rating == 5 else ("Enak dan murah." if rating == 4 else "Biasa saja.")
                reviews.append(Review(
                    store_id=p.store_id, product_id=p.id, user_id=c_id,
                    description=desc, rating=rating, label="Enak,Murah" if rating >= 4 else "Biasa",
                    is_image=False
                ))
        session.add_all(reviews)
        await session.flush()

        for s_id in store_ids:
            st_revs = [r for r in reviews if r.store_id == s_id]
            if st_revs:
                avg_rating = round(sum(r.rating for r in st_revs) / len(st_revs), 1)
                await session.execute(
                    text("UPDATE stores SET rating = :rating WHERE id = :sid"),
                    {"rating": avg_rating, "sid": s_id}
                )
        await session.commit()

        # 6. Seed Chat Conversations
        if customer_ids:
            c1 = Conversation(user_id=customer_ids[0], store_id=store_ids[0], title="Tanya stok roti")
            session.add(c1)
            await session.flush()

            m1 = ChatMessage(conversation_id=c1.id, role="user", content="Halo, apakah Roti Tawar Gandum masih ready?")
            session.add(m1)
            await session.flush()

            m2 = ChatMessage(conversation_id=c1.id, role="assistant", content="Halo! Ya, Roti Tawar Gandum kami saat ini masih ready stok di toko Tebet. Silakan diorder!")
            session.add(m2)
            await session.flush()

            tc1 = ToolCall(
                chat_message_id=m2.id, tool_name="product_search_tool",
                tool_input='{"query": "Roti Tawar Gandum"}',
                tool_output='{"name": "Roti Tawar Gandum", "stock": 15}'
            )
            session.add(tc1)

            cm1 = ChatMemory(user_id=customer_ids[0], key="favorite_product_type", value="bakery")
            cm2 = ChatMemory(user_id=customer_ids[1] if len(customer_ids) > 1 else customer_ids[0], key="favorite_product_type", value="produce")
            session.add_all([cm1, cm2])

        await session.commit()
        return total_orders_generated
