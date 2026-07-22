import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = 'postgresql+asyncpg://postgres:password123@127.0.0.1:5432/resurva'

async def cleanup():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Finding all dummy test stores in the database...")
        
        query = """
            SELECT id, name FROM stores 
            WHERE name LIKE '%Branch%' 
               OR name LIKE '%Green Store%' 
               OR name LIKE '%Test Store%' 
               OR name LIKE '%Search Store%' 
               OR name LIKE '%Upgraded Store%' 
               OR name LIKE '%Wallet Store%' 
               OR name LIKE '%Resurva Test Store%'
               OR name LIKE '%Supermart%'
        """
        res = await conn.execute(text(query))
        stores = res.all()
        
        if not stores:
            print("No dummy test stores found.")
            return
            
        print(f"Found {len(stores)} dummy stores to delete.")
        
        for store in stores:
            store_id, store_name = store
            print(f"Deleting store: {store_name} ({store_id})...")
            
            # 1. Delete order item variant options
            await conn.execute(text("""
                DELETE FROM order_item_variant_options 
                WHERE order_item_id IN (
                    SELECT oi.id FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.store_id = :store_id
                )
            """), {"store_id": store_id})
            
            # 2. Delete order item batches
            await conn.execute(text("""
                DELETE FROM order_item_batches 
                WHERE order_item_id IN (
                    SELECT oi.id FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.store_id = :store_id
                )
            """), {"store_id": store_id})
            
            # 3. Delete order items
            await conn.execute(text("""
                DELETE FROM order_items 
                WHERE order_id IN (
                    SELECT id FROM orders WHERE store_id = :store_id
                )
            """), {"store_id": store_id})
            
            # 4. Delete wallet transactions
            await conn.execute(text("""
                DELETE FROM wallet_transactions 
                WHERE transaction_id IN (
                    SELECT id FROM transactions 
                    WHERE order_id IN (
                        SELECT id FROM orders WHERE store_id = :store_id
                    )
                )
            """), {"store_id": store_id})
            
            # 5. Delete escrows, transactions, inventory transactions, carbon logs, reviews, orders
            await conn.execute(text("DELETE FROM order_escrows WHERE order_id IN (SELECT id FROM orders WHERE store_id = :store_id)"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM transactions WHERE store_id = :store_id"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM inventory_transactions WHERE store_id = :store_id"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM carbon_logs WHERE order_id IN (SELECT id FROM orders WHERE store_id = :store_id)"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM reviews WHERE store_id = :store_id"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM orders WHERE store_id = :store_id"), {"store_id": store_id})
            
            # 6. Delete inventory batches & products
            await conn.execute(text("DELETE FROM inventory_batches WHERE store_id = :store_id"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM products WHERE store_id = :store_id"), {"store_id": store_id})
            
            # 7. Delete wallets & stores
            await conn.execute(text("DELETE FROM wallets WHERE store_id = :store_id"), {"store_id": store_id})
            await conn.execute(text("DELETE FROM stores WHERE id = :store_id"), {"store_id": store_id})
            print(f"Deleted store {store_name} completely.")
            
        print("Cleanup of all dummy stores completed successfully!")

if __name__ == "__main__":
    asyncio.run(cleanup())
