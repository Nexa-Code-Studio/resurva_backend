import asyncio
import logging
from sqlalchemy import text
from app.core.logging import setup_logging
from app.db.session import SessionLocal

# Import modular seeders
from app.db.seeders.business_seeder import BusinessSeeder
from app.db.seeders.user_seeder import UserSeeder
from app.db.seeders.product_seeder import ProductSeeder
from app.db.seeders.order_seeder import OrderSeeder

# Initialize logging
setup_logging()
logger = logging.getLogger("app.db.seeders")


async def clear_database(session) -> None:
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
        "store_categories",
        "stores",
        "businesses",
    ]
    truncate_query = f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"
    await session.execute(text(truncate_query))
    await session.commit()
    logger.info("Database cleared successfully.")


async def seed_data() -> None:
    """Seeds the database with high-volume realistic sample data using modular seeders."""
    async with SessionLocal() as session:
        try:
            # 1. Clear database tables
            await clear_database(session)

            logger.info("Starting database seed via modular orchestrator...")

            # 2. Run BusinessSeeder
            b_ids, s_ids, w_ids = await BusinessSeeder.seed(session)

            # 3. Run UserSeeder
            user_ids_map = await UserSeeder.seed(
                session=session,
                business_ids=b_ids,
                store_ids=s_ids
            )

            # 4. Run ProductSeeder
            products, ingredients_map, prod_ing_maps, discounts = await ProductSeeder.seed(
                session=session,
                store_ids=s_ids
            )

            # 5. Run OrderSeeder (Simulate order histories and FEFO allocation)
            total_orders = await OrderSeeder.seed(
                session=session,
                store_ids=s_ids,
                wallet_ids=w_ids,
                customer_ids=user_ids_map["customers"],
                products=products,
                prod_ing_maps=prod_ing_maps,
                ingredients_map=ingredients_map,
                discounts=discounts
            )

            # 6. Commit the final additions
            await session.commit()
            logger.info(f"Database seeding completed successfully! Seeded a total of {total_orders} orders.")

        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_data())
