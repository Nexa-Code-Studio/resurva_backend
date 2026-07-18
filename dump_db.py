import asyncio
import uuid
import app.main
from sqlalchemy import select
from app.db.session import SessionLocal
from app.modules.users.models import User
from app.modules.stores.models import Store
from app.modules.products.models import Product

async def main():
    async with SessionLocal() as session:
        # Get all users
        res_users = await session.execute(select(User))
        users = res_users.scalars().all()
        print("=== USERS ===")
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | Store ID: {u.store_id}")
            
        # Get all stores
        res_stores = await session.execute(select(Store))
        stores = res_stores.scalars().all()
        print("\n=== STORES ===")
        for s in stores:
            # count products
            prod_res = await session.execute(select(Product).where(Product.store_id == s.id))
            prods = prod_res.scalars().all()
            prod_names = [p.name for p in prods]
            print(f"ID: {s.id} | Name: {s.name} | Product Count: {len(prods)}")
            print(f"  Products: {', '.join(prod_names[:10])}")

if __name__ == "__main__":
    asyncio.run(main())
