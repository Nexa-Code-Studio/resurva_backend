import os
import shutil
import asyncio
import logging
from app.main import app
from sqlalchemy import select
from app.db.session import SessionLocal
from app.modules.stores.models import Store
from app.modules.products.models import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scripts.assign_images_and_stores")

async def main():
    logger.info("Initializing directory copy...")
    
    # 1. Copy store default images
    src_store_dir = "/home/mashupsoat/Project/resurva/uploads/default/store"
    dest_store_dir = "uploads/stores"
    os.makedirs(dest_store_dir, exist_ok=True)
    if os.path.exists(src_store_dir):
        logger.info(f"Copying store images from {src_store_dir} to {dest_store_dir}...")
        for filename in os.listdir(src_store_dir):
            if filename.endswith(".png"):
                shutil.copy(
                    os.path.join(src_store_dir, filename),
                    os.path.join(dest_store_dir, filename)
                )
    else:
        logger.warning(f"Source store directory {src_store_dir} does not exist!")

    # 2. Copy product default images
    src_prod_dir = "/home/mashupsoat/Project/resurva/uploads/default/product"
    dest_prod_dir = "uploads/products"
    os.makedirs(dest_prod_dir, exist_ok=True)
    if os.path.exists(src_prod_dir):
        logger.info(f"Copying product images from {src_prod_dir} to {dest_prod_dir}...")
        for filename in os.listdir(src_prod_dir):
            if filename.endswith(".png"):
                shutil.copy(
                    os.path.join(src_prod_dir, filename),
                    os.path.join(dest_prod_dir, filename)
                )
    else:
        logger.warning(f"Source product directory {src_prod_dir} does not exist!")

    # 3. Assign images round-robin to all stores and products in the database
    async with SessionLocal() as session:
        try:
            # Update Stores
            stores_result = await session.execute(select(Store))
            stores = stores_result.scalars().all()
            logger.info(f"Found {len(stores)} stores in database. Updating image_urls...")
            for idx, store in enumerate(stores):
                img_num = (idx % 8) + 1
                store.image_url = f"/uploads/stores/{img_num}.png"

            # Update Products
            products_result = await session.execute(select(Product))
            products = products_result.scalars().all()
            logger.info(f"Found {len(products)} products in database. Updating image_urls...")
            for idx, prod in enumerate(products):
                img_num = (idx % 10) + 1
                prod.image_url = f"/uploads/products/{img_num}.png"

            await session.commit()
            logger.info("Database updated successfully!")
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(main())
