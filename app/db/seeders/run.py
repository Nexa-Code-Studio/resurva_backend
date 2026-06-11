import asyncio
import logging
import random
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import (
    DiscountType,
    ExpiryAlertStatus,
    OrderChannel,
    OrderStatus,
    PaymentMethod,
    ProductType,
    TransactionStatus,
    UserRole,
    WalletTransactionType,
)
from app.core.logging import setup_logging
from app.core.security import get_password_hash
from app.db.session import SessionLocal

# Import models
from app.modules.business.models import Business
from app.modules.carbon.models import CarbonLog
from app.modules.chat.models import ChatMemory, ChatMessage, Conversation, ToolCall
from app.modules.discounts.models import Discount
from app.modules.orders.models import Order, OrderDiscount, OrderItem, OrderItemBatch
from app.modules.inventory.models import ExpiryAlert, InventoryBatch
from app.modules.products.models import Ingredient, Product, ProductIngredient
from app.modules.reviews.models import Review
from app.modules.stores.models import Store
from app.modules.summaries.models import DailySummary, MonthlySummary
from app.modules.transactions.models import Transaction
from app.modules.users.models import User
from app.modules.wallets.models import Wallet, WalletTransaction

# Initialize logging
setup_logging()
logger = logging.getLogger("app.db.seeders")


async def clear_database(session: AsyncSession):
    """Truncates all tables to ensure clean seed data."""
    logger.info("Clearing existing data from database...")
    tables = [
        "order_item_batches",
        "chat_tool_calls",
        "chat_messages",
        "conversations",
        "chat_memories",
        "reviews",
        "monthly_summaries",
        "daily_summaries",
        "wallet_transactions",
        "wallets",
        "transactions",
        "carbon_logs",
        "order_discounts",
        "order_items",
        "orders",
        "discounts",
        "expiry_alerts",
        "inventory_batches",
        "product_ingredients",
        "ingredients",
        "products",
        "users",
        "stores",
        "businesses",
    ]
    truncate_query = f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"
    await session.execute(text(truncate_query))
    await session.commit()
    logger.info("Database cleared successfully.")


async def seed_data():
    """Seeds the database with high-volume (~60,000+), highly realistic sample data with FEFO batching."""
    async with SessionLocal() as session:
        try:
            await clear_database(session)

            logger.info("Starting high-volume database seed...")

            # 1. Generate standard password hash for all users
            hashed_password = get_password_hash("password123")

            # 2. Pre-generate UUIDs for core entities
            b_ids = [uuid.uuid4() for _ in range(3)]
            s_ids = [uuid.uuid4() for _ in range(3)]
            w_ids = [uuid.uuid4() for _ in range(3)]
            cust_ids = [uuid.uuid4() for _ in range(50)]
            owner_ids = [uuid.uuid4() for _ in range(3)]
            seller_ids = [uuid.uuid4() for _ in range(3)]
            admin_id = uuid.uuid4()

            # 3. Seed Businesses
            logger.info("Creating businesses...")
            businesses = [
                Business(id=b_ids[0], name="Roti & Cake Sentosa", email="sentosa.bakery@example.com", phone="021-5551234"),
                Business(id=b_ids[1], name="Green Grocer Indonesia", email="info@greengrocer.example.com", phone="021-5555678"),
                Business(id=b_ids[2], name="Mpok Siti Catering", email="mpoksiti@example.com", phone="0812-88889999")
            ]
            session.add_all(businesses)

            # 4. Seed Stores
            logger.info("Creating stores...")
            stores = [
                Store(
                    id=s_ids[0], business_id=b_ids[0], name="Sentosa Bakery - Tebet",
                    address="Jl. Tebet Raya No. 45", city="Jakarta Selatan", rating=4.8,
                    is_active=True, longitude=106.8483, latitude=-6.2305
                ),
                Store(
                    id=s_ids[1], business_id=b_ids[1], name="Green Grocer - Menteng",
                    address="Jl. Menteng Raya No. 12", city="Jakarta Pusat", rating=4.5,
                    is_active=True, longitude=106.8331, latitude=-6.1873
                ),
                Store(
                    id=s_ids[2], business_id=b_ids[2], name="Dapur Mpok Siti - Panglima Polim",
                    address="Jl. Panglima Polim No. 78", city="Jakarta Selatan", rating=4.6,
                    is_active=True, longitude=106.7984, latitude=-6.2443
                )
            ]
            session.add_all(stores)

            # 5. Seed Wallets
            logger.info("Creating wallets...")
            wallets = [
                Wallet(id=w_ids[0], store_id=s_ids[0], balance=0),
                Wallet(id=w_ids[1], store_id=s_ids[1], balance=0),
                Wallet(id=w_ids[2], store_id=s_ids[2], balance=0)
            ]
            session.add_all(wallets)

            # 6. Seed Users (50 Customers + Owners/Sellers)
            logger.info("Creating users...")
            users = [
                User(id=owner_ids[0], business_id=b_ids[0], username="owner_sentosa", email="owner_sentosa@example.com", password=hashed_password, role=UserRole.OWNER),
                User(id=seller_ids[0], business_id=b_ids[0], username="seller_sentosa", email="seller_sentosa@example.com", password=hashed_password, role=UserRole.SELLER),
                User(id=owner_ids[1], business_id=b_ids[1], username="owner_green", email="owner_green@example.com", password=hashed_password, role=UserRole.OWNER),
                User(id=seller_ids[1], business_id=b_ids[1], username="seller_green", email="seller_green@example.com", password=hashed_password, role=UserRole.SELLER),
                User(id=owner_ids[2], business_id=b_ids[2], username="owner_mpoksiti", email="owner_mpoksiti@example.com", password=hashed_password, role=UserRole.OWNER),
                User(id=seller_ids[2], business_id=b_ids[2], username="seller_mpoksiti", email="seller_mpoksiti@example.com", password=hashed_password, role=UserRole.SELLER),
                User(id=admin_id, username="super_admin", email="admin@resurva.com", password=hashed_password, role=UserRole.ADMIN)
            ]

            first_names = ["Budi", "Siti", "Ani", "Dodi", "Eka", "Rizky", "Dewi", "Agus", "Mega", "Hendra", "Yanto", "Rina", "Adit", "Fitri", "Tono", "Wati", "Andi", "Sri", "Joko", "Lilis"]
            last_names = ["Sutrisno", "Aminah", "Lestari", "Hermawan", "Pratama", "Hidayat", "Sari", "Wibowo", "Putri", "Wijaya", "Kusuma", "Santoso", "Sitorus", "Siregar", "Ginting", "Nasution", "Lubis", "Pasaribu", "Pohan", "Simanjuntak"]

            random.seed(42)
            generated_usernames = set()
            for idx in range(50):
                while True:
                    f_name = random.choice(first_names)
                    l_name = random.choice(last_names)
                    username = f"{f_name.lower()}_{l_name.lower()}_{random.randint(10, 99)}"
                    if username not in generated_usernames:
                        generated_usernames.add(username)
                        break

                users.append(User(
                    id=cust_ids[idx],
                    username=username,
                    email=f"{username}@example.com",
                    password=hashed_password,
                    role=UserRole.CUSTOMER
                ))
            session.add_all(users)
            await session.flush()

            # 7. Seed Ingredients
            logger.info("Creating ingredients...")
            ing_configs = [
                ("Tepung Terigu", "gram", 0.0015),
                ("Mentega", "gram", 0.0080),
                ("Telur", "pcs", 0.3000),
                ("Gula Pasir", "gram", 0.0020),
                ("Cokelat Bubuk", "gram", 0.0120),
                ("Susu Cair", "ml", 0.0030),
                ("Sayur Bayam", "gram", 0.0005),
                ("Wortel", "gram", 0.0004),
                ("Tomat", "gram", 0.0008),
                ("Daging Ayam", "gram", 0.0069),
                ("Beras", "gram", 0.0025),
                ("Daging Sapi", "gram", 0.0270),
                ("Santan", "ml", 0.0022),
                ("Cabai", "gram", 0.0010),
                ("Tempe", "gram", 0.0009),
                ("Tahu", "gram", 0.0011),
                ("Plastik Kemasan", "pcs", 0.0500)
            ]
            ingredients_map = {}
            for name, unit, carbon in ing_configs:
                ing = Ingredient(name=name, unit=unit, carbon_per_unit=carbon)
                session.add(ing)
                ingredients_map[name] = ing

            await session.flush()

            # 8. Seed Products (30 items)
            logger.info("Creating products...")
            p_configs = [
                # Store 1 - Sentosa Bakery
                (s_ids[0], "Roti Tawar Gandum", ProductType.BAKERY, 20000, 10000, "Roti gandum utuh berserat tinggi."),
                (s_ids[0], "Croissant Cokelat", ProductType.BAKERY, 15000, 8000, "Croissant cokelat renyah bumbu mentega."),
                (s_ids[0], "Kue Sus Fla Vanila", ProductType.BAKERY, 8000, 4000, "Kue sus manis isi vanila segar."),
                (s_ids[0], "Brownies Panggang", ProductType.BAKERY, 65000, 35000, "Brownies panggang premium almond topping."),
                (s_ids[0], "Donat Kentang Gula", ProductType.BAKERY, 7000, 3500, "Donat kentang tradisional tabur gula pasir halus."),
                (s_ids[0], "Baguette Perancis", ProductType.BAKERY, 18000, 9000, "Roti baguette panjang renyah khas Perancis."),
                (s_ids[0], "Roti Keset Keju", ProductType.BAKERY, 25000, 15000, "Roti sobek lembut isi keju cheddar melimpah."),
                (s_ids[0], "Cinnamon Roll", ProductType.BAKERY, 16000, 10000, "Roti gulung aroma kayu manis dengan krim keju cair."),
                (s_ids[0], "Muffin Blueberry", ProductType.BAKERY, 12000, 7000, "Muffin blueberry manis dengan crumble renyah."),
                (s_ids[0], "Roti Abon Sapi", ProductType.BAKERY, 14000, 8000, "Roti manis lembut dengan taburan abon sapi gurih."),

                # Store 2 - Green Grocer
                (s_ids[1], "Sayur Bayam Organik", ProductType.PRODUCE, 12000, 5000, "Bayam segar hidroponik bebas pestisida."),
                (s_ids[1], "Susu UHT Full Cream 1L", ProductType.PACKAGED, 25000, 15000, "Susu UHT steril kemasan karton 1 liter."),
                (s_ids[1], "Daging Dada Ayam 500g", ProductType.PRODUCE, 38000, 22000, "Fillet dada ayam segar tanpa tulang."),
                (s_ids[1], "Tomat Ceri 250g", ProductType.PRODUCE, 18000, 9000, "Tomat ceri merah segar manis asam."),
                (s_ids[1], "Beras Pandan Wangi 5kg", ProductType.PACKAGED, 85000, 68000, "Beras pandan wangi pulen Cianjur asli."),
                (s_ids[1], "Wortel Lokal 1kg", ProductType.PRODUCE, 15000, 8000, "Wortel lokal segar manis kaya vitamin A."),
                (s_ids[1], "Minyak Goreng 2L", ProductType.PACKAGED, 40000, 32000, "Minyak goreng kelapa sawit murni kemasan pouch."),
                (s_ids[1], "Bawang Merah Kupas 250g", ProductType.PRODUCE, 20000, 12000, "Bawang merah kupas segar siap masak."),
                (s_ids[1], "Telur Ayam Negeri 10 Butir", ProductType.PRODUCE, 22000, 15000, "Telur ayam segar pilihan isi 10 butir."),
                (s_ids[1], "Kecap Manis Botol 275ml", ProductType.PACKAGED, 12000, 9000, "Kecap manis kental dari kedelai hitam pilihan."),

                # Store 3 - Dapur Mpok Siti
                (s_ids[2], "Nasi Rames Ayam Bakar", ProductType.READY_TO_EAT, 28000, 14000, "Nasi rames dengan lauk ayam bakar dan lalapan."),
                (s_ids[2], "Rendang Sapi Porsi", ProductType.READY_TO_EAT, 35000, 18000, "Rendang daging sapi bumbu Padang asli."),
                (s_ids[2], "Sayur Lodeh Betawi", ProductType.READY_TO_EAT, 15000, 7500, "Sayur lodeh kuah santan gurih melimpah."),
                (s_ids[2], "Tempe & Tahu Bacem", ProductType.READY_TO_EAT, 12000, 6000, "Tempe tahu bacem manis legit isi 4."),
                (s_ids[2], "Nasi Goreng Spesial", ProductType.READY_TO_EAT, 22000, 12000, "Nasi goreng kecap dengan telur dadar dan acar."),
                (s_ids[2], "Soto Ayam Lamongan", ProductType.READY_TO_EAT, 20000, 11000, "Soto ayam kuah kuning gurih koya melimpah."),
                (s_ids[2], "Gado-Gado Siram", ProductType.READY_TO_EAT, 18000, 10000, "Gado-gado sayuran segar dengan bumbu kacang kental."),
                (s_ids[2], "Ayam Goreng Lengkuas", ProductType.READY_TO_EAT, 25000, 14000, "Ayam goreng kremes lengkuas gurih isi 2 potong."),
                (s_ids[2], "Sambal Goreng Ati Ampela", ProductType.READY_TO_EAT, 16000, 9000, "Sambal goreng ati ampela kentang dadu pedas manis."),
                (s_ids[2], "Orek Tempe Basah", ProductType.READY_TO_EAT, 10000, 5000, "Tempe orek bumbu kecap manis gurih porsi keluarga.")
            ]
            products = []
            products_dict = {}
            for st_id, name, p_type, orig, disc, desc in p_configs:
                p = Product(
                    store_id=st_id, name=name, product_type=p_type,
                    original_price=orig, discounted_price=disc,
                    description=desc, stock=0, sold=0,
                    expired_at=datetime.now(UTC) + timedelta(days=2)
                )
                products.append(p)
                session.add(p)

            await session.flush()
            for p in products:
                products_dict[p.id] = p

            # 9. Link ProductIngredients
            logger.info("Linking products with ingredients...")
            prod_ing_maps = []
            for p in products:
                p_ings = random.sample(list(ingredients_map.keys()), random.randint(1, 3))
                for ing_name in p_ings:
                    ing_obj = ingredients_map[ing_name]
                    qty = random.uniform(10.0, 300.0) if ing_obj.unit != "pcs" else random.randint(1, 3)
                    prod_ing_maps.append(ProductIngredient(
                        product_id=p.id,
                        ingredient_id=ing_obj.id,
                        quantity=round(qty, 2)
                    ))
            session.add_all(prod_ing_maps)
            await session.flush()

            # 10. Seed Store Discounts
            logger.info("Creating store discounts...")
            discounts = [
                Discount(
                    store_id=s_ids[0], name="Diskon Sore Bakery", type=DiscountType.PERCENTAGE, value=50, quota=100000,
                    code="SOREBAKERY50", start_time=datetime.now(UTC) - timedelta(days=2000), end_time=datetime.now(UTC) + timedelta(days=2000)
                ),
                Discount(
                    store_id=s_ids[1], name="Voucher Hemat Hijau", type=DiscountType.FIXED, value=5000, quota=100000,
                    code="HEMAT5K", start_time=datetime.now(UTC) - timedelta(days=2000), end_time=datetime.now(UTC) + timedelta(days=2000), is_voucher=True
                ),
                Discount(
                    store_id=s_ids[2], name="Diskon Makan Siang Siti", type=DiscountType.PERCENTAGE, value=30, quota=100000,
                    code="SIANGSITI30", start_time=datetime.now(UTC) - timedelta(days=2000), end_time=datetime.now(UTC) + timedelta(days=2000)
                )
            ]
            session.add_all(discounts)
            await session.flush()

            store_products_map = {s_ids[0]: [], s_ids[1]: [], s_ids[2]: []}
            for p in products:
                store_products_map[p.store_id].append(p)

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

            # 11. Seeding timeline configuration
            # Option A: 1 Year (Default - Seeding in ~1-1.5 mins)
            days_history = 365
            # Option B: 3 Years (Seed in ~3-5 mins)
            # days_history = 1095
            # Option C: 5 Years (Seed in ~6-10 mins)
            # days_history = 1825

            end_date = date.today()
            start_date = end_date - timedelta(days=days_history)

            store_balances = {s_ids[0]: 0, s_ids[1]: 0, s_ids[2]: 0}
            daily_summaries_data = {}
            monthly_summaries_data = {}

            status_choices = [OrderStatus.COMPLETED, OrderStatus.PAID, OrderStatus.CANCELLED, OrderStatus.PENDING]
            status_weights = [0.90, 0.05, 0.03, 0.02]
            payment_choices = [PaymentMethod.QRIS, PaymentMethod.GOPAY, PaymentMethod.OVO, PaymentMethod.CASH, PaymentMethod.TRANSFER]

            # Lifespan dictionary per product type
            def get_product_lifespan(p_type):
                if p_type == ProductType.BAKERY:
                    return timedelta(days=1)
                elif p_type == ProductType.PRODUCE:
                    return timedelta(days=3)
                elif p_type == ProductType.READY_TO_EAT:
                    return timedelta(hours=12)
                elif p_type == ProductType.PACKAGED:
                    return timedelta(days=180)
                else:
                    return timedelta(days=30)

            # Store active batches (product_id -> list of active batch dicts)
            # Each batch dict: {id, product_id, store_id, quantity, remaining_quantity, expired_at}
            active_batches = {p.id: [] for p in products}

            # Final lists for bulk database insertions
            orders_chunk = []
            order_items_chunk = []
            order_item_batches_chunk = []
            order_discounts_chunk = []
            carbon_logs_chunk = []
            transactions_chunk = []
            wallet_transactions_chunk = []
            inventory_batches_chunk = []
            expiry_alerts_chunk = []

            # Track total products sold and stock updates in memory
            product_sales_tracker = {p.id: 0 for p in products}

            total_orders_generated = 0
            current_month = start_date.month
            curr_date = start_date

            logger.info("Starting historical data generation loop...")

            while curr_date <= end_date:
                # Dynamic Daily Base Order Density (Growth Trend)
                days_passed = (curr_date - start_date).days
                total_days = max(1, (end_date - start_date).days)
                progress = days_passed / total_days

                min_base = int(60 + (220 - 60) * progress)
                max_base = int(90 + (280 - 90) * progress)
                base_orders = random.randint(min_base, max_base)

                # Seasonality (Weekend boost)
                weekday = curr_date.weekday()
                if weekday in [4, 5, 6]:
                    order_count = int(base_orders * random.uniform(1.2, 1.4))
                else:
                    order_count = int(base_orders * random.uniform(0.8, 1.0))

                # Loop to generate daily orders
                for _ in range(order_count):
                    cust_id = random.choice(cust_ids)
                    store_id = random.choice(s_ids)
                    store_prods = store_products_map[store_id]
                    if not store_prods:
                        continue

                    chosen_prods = random.sample(store_prods, random.randint(1, min(3, len(store_prods))))

                    order_time = datetime(
                        curr_date.year, curr_date.month, curr_date.day,
                        random.randint(7, 21), random.randint(0, 59), random.randint(0, 59),
                        tzinfo=UTC
                    )

                    order_id = uuid.uuid4()
                    total_price = 0
                    carbon_saved = 0.0

                    order_items_to_create = []

                    for prod in chosen_prods:
                        qty = random.randint(1, 3)
                        subtotal = prod.discounted_price * qty
                        total_price += subtotal
                        carbon_saved += carbon_rates[prod.id] * qty

                        oi_id = uuid.uuid4()
                        order_items_to_create.append((oi_id, prod, qty, subtotal))

                        # Accumulate order item dict
                        order_items_chunk.append({
                            "id": oi_id,
                            "order_id": order_id,
                            "product_id": prod.id,
                            "quantity": qty,
                            "unit_price": prod.discounted_price,
                            "subtotal": subtotal
                        })

                        # --- FEFO BATCH ALLOCATION SYSTEM ---
                        p_batches = active_batches[prod.id]
                        # Filter active, non-expired, non-empty batches
                        valid_batches = [
                            b for b in p_batches
                            if b["expired_at"] > order_time and b["remaining_quantity"] > 0
                        ]
                        # Sort by expiration date ascending (FEFO)
                        valid_batches.sort(key=lambda x: x["expired_at"])

                        allocated_qty = 0
                        
                        # Loop through batches to deduct quantity
                        for b in valid_batches:
                            if allocated_qty >= qty:
                                break
                            take = min(qty - allocated_qty, b["remaining_quantity"])
                            b["remaining_quantity"] -= take
                            allocated_qty += take

                            # Record order item batch link
                            order_item_batches_chunk.append({
                                "id": uuid.uuid4(),
                                "order_item_id": oi_id,
                                "inventory_batch_id": b["id"],
                                "quantity": take
                            })

                        # If active batches are insufficient, create a new batch!
                        if allocated_qty < qty:
                            shortage = qty - allocated_qty
                            new_batch_id = uuid.uuid4()
                            batch_qty = shortage + random.randint(30, 80)
                            expired_at = order_time + get_product_lifespan(prod.product_type)

                            new_batch = {
                                "id": new_batch_id,
                                "product_id": prod.id,
                                "store_id": store_id,
                                "quantity": batch_qty,
                                "remaining_quantity": batch_qty - shortage,
                                "expired_at": expired_at
                            }
                            # Add to active list
                            active_batches[prod.id].append(new_batch)

                            # Accumulate batch for insert
                            inventory_batches_chunk.append({
                                "id": new_batch_id,
                                "product_id": prod.id,
                                "store_id": store_id,
                                "quantity": batch_qty,
                                "remaining_quantity": batch_qty, # Initial full qty for DB record
                                "expired_at": expired_at,
                                "created_at": order_time - timedelta(hours=random.randint(1, 4))
                            })

                            # Record allocation link for the shortage amount
                            order_item_batches_chunk.append({
                                "id": uuid.uuid4(),
                                "order_item_id": oi_id,
                                "inventory_batch_id": new_batch_id,
                                "quantity": shortage
                            })

                    # Decide on discount (20% chance)
                    total_discount = 0
                    disc_applied = None
                    if random.random() < 0.2:
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

                    # Choose status, channel, payment method
                    status = random.choices(status_choices, weights=status_weights, k=1)[0]
                    channel = OrderChannel.MARKETPLACE if random.random() < 0.85 else OrderChannel.KASIR
                    pm = random.choice(payment_choices)

                    # Accumulate Order
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
                        wallet_id = w_ids[0] if store_id == s_ids[0] else (w_ids[1] if store_id == s_ids[1] else w_ids[2])

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

                        # Sales tracker
                        for _, p_obj, item_qty, _ in order_items_to_create:
                            product_sales_tracker[p_obj.id] += item_qty

                        # Summaries accumulation
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

                # Clean up expired batches and write ExpiryAlerts (dynamic scan)
                for p_id, p_batches in active_batches.items():
                    expired_list = []
                    for b in p_batches:
                        if b["expired_at"] <= datetime(curr_date.year, curr_date.month, curr_date.day, 23, 59, 59, tzinfo=UTC):
                            expired_list.append(b)
                            if b["remaining_quantity"] > 0:
                                # Create an EXPIRED alert
                                expiry_alerts_chunk.append({
                                    "id": uuid.uuid4(),
                                    "product_id": b["product_id"],
                                    "store_id": b["store_id"],
                                    "days_until_expiry": -1,
                                    "status": ExpiryAlertStatus.EXPIRED,
                                    "alerted_at": b["expired_at"]
                                })
                    # Remove from active lists
                    for eb in expired_list:
                        p_batches.remove(eb)

                # Monthly chunk database insertion (keeps memory light)
                next_day = curr_date + timedelta(days=1)
                if next_day.month != current_month or next_day > end_date:
                    logger.info(f"Inserting monthly chunk {current_month}/{curr_date.year}... (Generated {total_orders_generated} orders total)")

                    # Write Batches first so FKs exist in order_item_batches
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

            # 13. Update final Store Wallet Balances & Product stocks/sold numbers
            for s_id, final_bal in store_balances.items():
                w_id = w_ids[0] if s_id == s_ids[0] else (w_ids[1] if s_id == s_ids[1] else w_ids[2])
                await session.execute(
                    text("UPDATE wallets SET balance = :bal, updated_at = :now WHERE id = :wid"),
                    {"bal": final_bal, "now": datetime.now(UTC), "wid": w_id}
                )

            # Sync products stock and sold columns
            for p in products:
                # Remaining active stock is sum of remaining quantities of currently active batches
                remaining_stock = sum(b["remaining_quantity"] for b in active_batches[p.id])
                sold_qty = product_sales_tracker[p.id]
                await session.execute(
                    text("UPDATE products SET stock = :st, sold = :sold WHERE id = :pid"),
                    {"st": remaining_stock, "sold": sold_qty, "pid": p.id}
                )

            # Update remaining_quantity on DB for inventory batches that were updated in seeder loop
            # (To ensure remaining quantity matches final remaining quantity of simulation)
            for p_id, p_batches in active_batches.items():
                for b in p_batches:
                    await session.execute(
                        text("UPDATE inventory_batches SET remaining_quantity = :rq WHERE id = :bid"),
                        {"rq": b["remaining_quantity"], "bid": b["id"]}
                    )
            await session.commit()

            # 14. Seed summaries objects
            logger.info("Inserting daily and monthly summaries...")
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
                    "expiry_alerts_count": random.randint(1, 4),
                    "created_at": datetime.combine(s_date, datetime.min.time(), tzinfo=UTC)
                })

            for i in range(0, len(daily_summary_list), 5000):
                await session.execute(insert(DailySummary), daily_summary_list[i:i + 5000])

            monthly_summary_list = []
            for (st_id, yr, mn), m_val in monthly_summaries_data.items():
                st_rating = 4.8 if st_id == s_ids[0] else (4.5 if st_id == s_ids[1] else 4.6)
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

            # 15. Seed Reviews
            logger.info("Creating reviews...")
            reviews = []
            for p in products:
                rev_custs = random.sample(cust_ids, random.randint(1, 2))
                for c_id in rev_custs:
                    rating = random.randint(3, 5)
                    desc = "Sangat direkomendasikan!" if rating == 5 else ("Enak dan murah." if rating == 4 else "Biasa saja.")
                    reviews.append(Review(
                        store_id=p.store_id, product_id=p.id, user_id=c_id,
                        description=desc, rating=rating, label="Enak,Murah" if rating >= 4 else "Biasa",
                        is_image=False
                    ))
            session.add_all(reviews)
            await session.flush()

            for s_id in s_ids:
                st_revs = [r for r in reviews if r.store_id == s_id]
                if st_revs:
                    avg_rating = round(sum(r.rating for r in st_revs) / len(st_revs), 1)
                    await session.execute(
                        text("UPDATE stores SET rating = :rating WHERE id = :sid"),
                        {"rating": avg_rating, "sid": s_id}
                    )
            await session.commit()

            # 16. Seed Chat Conversations & Messages
            logger.info("Creating conversations, messages, and memories...")
            c1 = Conversation(user_id=cust_ids[0], store_id=s_ids[0], title="Tanya stok roti")
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

            # Seed ChatMemory
            cm1 = ChatMemory(user_id=cust_ids[0], key="favorite_product_type", value="bakery")
            cm2 = ChatMemory(user_id=cust_ids[1], key="favorite_product_type", value="produce")
            session.add_all([cm1, cm2])

            await session.commit()
            logger.info(f"Database seeding completed successfully! Seeded a total of {total_orders_generated} orders.")

        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_data())
