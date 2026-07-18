import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = 'postgresql+asyncpg://postgres:password123@127.0.0.1:5432/resurva'

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Modifying database schema (v5)...")
        
        # Modify stores table columns
        res = await conn.execute(text("select column_name from information_schema.columns where table_name = 'stores'"))
        cols = {r[0] for r in res.all()}
        
        # Add categories_data if not exists
        if 'categories_data' not in cols:
            print("Adding stores.categories_data...")
            await conn.execute(text("ALTER TABLE stores ADD COLUMN categories_data TEXT;"))
            
        print("Database schema updates (v5) successfully applied!")

if __name__ == "__main__":
    asyncio.run(main())
