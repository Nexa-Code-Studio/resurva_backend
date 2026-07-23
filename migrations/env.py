import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Append current directory to path so app modules can be loaded
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base

# Import all models to ensure they are registered on Base.metadata for autogenerate
from app.modules.auth.models import RefreshToken
from app.modules.business.models import Business
from app.modules.users.models import User
from app.modules.stores.models import Store, EnterpriseRequest, StoreCategory
from app.modules.products.models import Product, Ingredient, ProductIngredient
from app.modules.inventory.models import InventoryBatch, ExpiryAlert
from app.modules.reviews.models import Review
from app.modules.discounts.models import Discount
from app.modules.orders.models import Order, OrderItem, OrderDiscount, OrderItemBatch
from app.modules.carbon.models import CarbonLog
from app.modules.transactions.models import Transaction
from app.modules.wallets.models import Wallet, WalletTransaction
from app.modules.summaries.models import DailySummary, MonthlySummary
from app.modules.chat.models import Conversation, ChatMessage, ToolCall, ChatMemory
from app.modules.verifications.models import PartnerVerification
from app.modules.cart.models import CartReservation


# Alembic Config
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.async_database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = create_async_engine(
        settings.async_database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
