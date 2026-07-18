import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = 'postgresql+asyncpg://postgres:password123@127.0.0.1:5432/resurva'

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Modifying database schema (v4)...")
        
        # 1. Modify products table columns
        res = await conn.execute(text("select column_name from information_schema.columns where table_name = 'products'"))
        cols = {r[0] for r in res.all()}
        
        # Alter product_type to VARCHAR
        print("Altering products.product_type to VARCHAR...")
        await conn.execute(text("ALTER TABLE products ALTER COLUMN product_type TYPE VARCHAR;"))
        
        # Add ingredients_data if not exists
        if 'ingredients_data' not in cols:
            print("Adding products.ingredients_data...")
            await conn.execute(text("ALTER TABLE products ADD COLUMN ingredients_data TEXT;"))
            
        print("Database schema updates (v4) successfully applied!")

if __name__ == "__main__":
    asyncio.run(main())
