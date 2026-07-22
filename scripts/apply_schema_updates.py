import asyncio
import uuid
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = 'postgresql+asyncpg://postgres:password123@127.0.0.1:5432/resurva'

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Modifying database schema...")

        # Modify stores table (add operating_hours)
        res_stores = await conn.execute(text("select column_name from information_schema.columns where table_name = 'stores'"))
        stores_cols = {r[0] for r in res_stores.all()}
        
        # Modify reviews table (add order_id)
        res_reviews = await conn.execute(text("select column_name from information_schema.columns where table_name = 'reviews'"))
        reviews_cols = {r[0] for r in res_reviews.all()}
        if 'order_id' not in reviews_cols:
            print("Adding reviews.order_id...")
            await conn.execute(text("ALTER TABLE reviews ADD COLUMN order_id UUID REFERENCES orders(id) ON DELETE SET NULL;"))
        if 'operating_hours' not in stores_cols:
            print("Adding stores.operating_hours...")
            await conn.execute(text("ALTER TABLE stores ADD COLUMN operating_hours VARCHAR;"))
            # Backfill existing data: copy pickup_time (which was opening hours) to operating_hours
            print("Backfilling stores.operating_hours from pickup_time...")
            await conn.execute(text("UPDATE stores SET operating_hours = pickup_time WHERE operating_hours IS NULL;"))
            # Reset pickup_time to default "19:30 - 21:00 WIB" so they don't default to the store's opening hours
            print("Resetting stores.pickup_time to default surplus pickup window...")
            await conn.execute(text("UPDATE stores SET pickup_time = '19:30 - 21:00 WIB';"))

        # Modify users table (add full_name, phone_number, photo_url)
        res_users = await conn.execute(text("select column_name from information_schema.columns where table_name = 'users'"))
        users_cols = {r[0] for r in res_users.all()}
        if 'full_name' not in users_cols:
            print("Adding users.full_name...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR;"))
            # Backfill full_name with username
            await conn.execute(text("UPDATE users SET full_name = username WHERE full_name IS NULL;"))
        if 'phone_number' not in users_cols:
            print("Adding users.phone_number...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR;"))
        if 'photo_url' not in users_cols:
            print("Adding users.photo_url...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN photo_url VARCHAR;"))
        
        # 1. Modify products table
        # Check if columns already exist first
        res = await conn.execute(text("select column_name from information_schema.columns where table_name = 'products'"))
        cols = {r[0] for r in res.all()}
        
        if 'sku' not in cols:
            print("Adding products.sku...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN sku VARCHAR;"))
        if 'weight' not in cols:
            print("Adding products.weight...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN weight FLOAT DEFAULT 0.1;"))
        if 'is_published' not in cols:
            print("Adding products.is_published...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN is_published BOOLEAN DEFAULT TRUE;"))
        if 'auto_surplus_enabled' not in cols:
            print("Adding products.auto_surplus_enabled...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN auto_surplus_enabled BOOLEAN DEFAULT FALSE;"))
        if 'surplus_trigger_hours' not in cols:
            print("Adding products.surplus_trigger_hours...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN surplus_trigger_hours INTEGER DEFAULT 0;"))
        if 'supplier_lead_time_days' not in cols:
            print("Adding products.supplier_lead_time_days...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN supplier_lead_time_days INTEGER DEFAULT 2;"))

        # Modify orders table
        res_orders = await conn.execute(text("select column_name from information_schema.columns where table_name = 'orders'"))
        orders_cols = {r[0] for r in res_orders.all()}
        if 'notes' not in orders_cols:
            print("Adding orders.notes...")
            await conn.execute(text("ALTER TABLE orders ADD COLUMN notes VARCHAR;"))
        if 'daily_code' not in orders_cols:
            print("Adding orders.daily_code...")
            await conn.execute(text("ALTER TABLE orders ADD COLUMN daily_code VARCHAR;"))
            
        # 2. Modify inventory_batches table
        res = await conn.execute(text("select column_name from information_schema.columns where table_name = 'inventory_batches'"))
        ib_cols = {r[0] for r in res.all()}
        
        if 'batch_tag' not in ib_cols:
            print("Adding inventory_batches.batch_tag...")
            await conn.execute(text("ALTER TABLE inventory_batches ADD COLUMN batch_tag VARCHAR;"))
            
        if 'available_from' in ib_cols and 'surplus_starts_at' not in ib_cols:
            print("Renaming available_from to surplus_starts_at...")
            await conn.execute(text("ALTER TABLE inventory_batches RENAME COLUMN available_from TO surplus_starts_at;"))
        elif 'surplus_starts_at' not in ib_cols:
            print("Adding inventory_batches.surplus_starts_at...")
            await conn.execute(text("ALTER TABLE inventory_batches ADD COLUMN surplus_starts_at TIMESTAMP WITH TIME ZONE;"))
            
        # 3. Create product_variant_groups table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_variant_groups (
                id UUID PRIMARY KEY,
                product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                is_required BOOLEAN NOT NULL DEFAULT FALSE,
                max_selections INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        print("Table product_variant_groups created/verified.")
        
        # 4. Create product_variant_options table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_variant_options (
                id UUID PRIMARY KEY,
                variant_group_id UUID NOT NULL REFERENCES product_variant_groups(id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                additional_price INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        print("Table product_variant_options created/verified.")
        
        # 5. Create order_item_variant_options table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS order_item_variant_options (
                id UUID PRIMARY KEY,
                order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
                variant_option_id UUID REFERENCES product_variant_options(id) ON DELETE SET NULL,
                name VARCHAR NOT NULL,
                additional_price INTEGER NOT NULL DEFAULT 0
            );
        """))
        print("Table order_item_variant_options created/verified.")
        
        # 6. Create inventory_transactions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id UUID PRIMARY KEY,
                product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                inventory_batch_id UUID REFERENCES inventory_batches(id) ON DELETE SET NULL,
                batch_tag VARCHAR,
                type VARCHAR NOT NULL,
                quantity INTEGER NOT NULL,
                reason VARCHAR NOT NULL,
                reference VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        print("Table inventory_transactions created/verified.")

        # Create order_escrows table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS order_escrows (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
                store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'held',
                released_at TIMESTAMP WITH TIME ZONE,
                refunded_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        print("Table order_escrows created/verified.")
        
    async with engine.connect() as conn:
        # Alter orderstatus enum type to add 'prepared' and 'PREPARED' values if not exists
        try:
            await conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'prepared';"))
            print("Enum value 'prepared' added/verified in orderstatus type.")
        except Exception as e:
            print(f"Warning/info updating orderstatus enum (prepared): {e}")

        try:
            await conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'PREPARED';"))
            print("Enum value 'PREPARED' added/verified in orderstatus type.")
        except Exception as e:
            print(f"Warning/info updating orderstatus enum (PREPARED): {e}")

        try:
            await conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'confirmed';"))
            print("Enum value 'confirmed' added/verified in orderstatus type.")
        except Exception as e:
            print(f"Warning/info updating orderstatus enum (confirmed): {e}")

        try:
            await conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'CONFIRMED';"))
            print("Enum value 'CONFIRMED' added/verified in orderstatus type.")
        except Exception as e:
            print(f"Warning/info updating orderstatus enum (CONFIRMED): {e}")

        # 7. Generate SKUs for existing products that don't have it
        print("Updating/generating SKUs for existing products...")
        res = await conn.execute(text("select id, name, sku from products"))
        products = res.all()
        
        updated_skus = 0
        for i, prod in enumerate(products):
            pid, pname, psku = prod
            if not psku:
                # Generate simple SKU, e.g. BKR-001 or PROD-001 based on product type
                # Let's see category to guess a prefix
                prefix = "PRD"
                if "roti" in pname.lower() or "kue" in pname.lower() or "bread" in pname.lower():
                    prefix = "BKR"
                elif "kopi" in pname.lower() or "teh" in pname.lower() or "jus" in pname.lower() or "drink" in pname.lower():
                    prefix = "MNM"
                else:
                    prefix = "FOD"
                new_sku = f"{prefix}-{100 + i}"
                await conn.execute(text("update products set sku = :sku where id = :id"), {"sku": new_sku, "id": pid})
                updated_skus += 1
        print(f"Generated SKUs for {updated_skus} products.")
        await conn.commit()

        # 8. Backfill batch tags for all existing batches
        print("Backfilling batch tags for existing inventory batches...")
        res = await conn.execute(text("select id, sku from products"))
        product_skus = {r[0]: r[1] for r in res.all()}
        
        # We query and update batches by product to cleanly group them by date
        total_backfilled = 0
        for pid, sku in product_skus.items():
            # Get all batches of this product ordered by expired_at and created_at
            res = await conn.execute(
                text("select id, expired_at from inventory_batches where product_id = :pid order by expired_at asc, created_at asc"),
                {"pid": pid}
            )
            batches = res.all()
            if not batches:
                continue
                
            # Group by day and format: {sku}_{dateStr}_{letter}
            day_counts = {}
            for bid, expired_at in batches:
                # Format to local string format
                date_str = expired_at.strftime("%d%m%Y")
                count = day_counts.get(date_str, 0)
                letter = chr(65 + count)
                day_counts[date_str] = count + 1
                
                tag = f"{sku}_{date_str}_{letter}"
                # Update in DB
                await conn.execute(
                    text("update inventory_batches set batch_tag = :tag where id = :id"),
                    {"tag": tag, "id": bid}
                )
                total_backfilled += 1
                
        print(f"Backfilled batch tags for {total_backfilled} inventory batches.")
        await conn.commit()

        # 9. Backfill daily_code for existing orders
        print("Backfilling daily_code for existing orders...")
        res_orders = await conn.execute(text("select id, store_id, created_at from orders order by store_id, created_at asc"))
        all_db_orders = res_orders.all()
        
        # Track counts grouped by (store_id, date)
        order_day_trackers = {}
        updated_orders_count = 0
        for oid, store_id, created_at in all_db_orders:
            order_date = created_at.date()
            key = (store_id, order_date)
            
            current_count = order_day_trackers.get(key, 0) + 1
            order_day_trackers[key] = current_count
            
            weekday = order_date.weekday() # 0 = Monday, 6 = Sunday
            prefix = chr(ord('A') + weekday)
            
            daily_code = f"{prefix}-{current_count}"
            
            await conn.execute(
                text("update orders set daily_code = :daily_code where id = :id"),
                {"daily_code": daily_code, "id": oid}
            )
            updated_orders_count += 1
            
        print(f"Backfilled daily_code for {updated_orders_count} orders.")
        await conn.commit()
        
    print("Database updates successfully applied!")

if __name__ == '__main__':
    asyncio.run(main())
