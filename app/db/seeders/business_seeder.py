import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.business.models import Business
from app.modules.stores.models import Store
from app.modules.wallets.models import Wallet

logger = logging.getLogger("app.db.seeders.business")

class BusinessSeeder:
    @staticmethod
    async def seed(session: AsyncSession) -> tuple[list[uuid.UUID], list[uuid.UUID], list[uuid.UUID]]:
        """
        Seeds businesses, stores, and wallets.
        Returns a tuple of (business_ids, store_ids, wallet_ids).
        """
        logger.info("Seeding businesses, stores, and wallets...")

        b_ids = [uuid.uuid4() for _ in range(3)]
        s_ids = [uuid.uuid4() for _ in range(3)]
        w_ids = [uuid.uuid4() for _ in range(3)]

        # 1. Seed Businesses
        businesses = [
            Business(id=b_ids[0], name="Roti & Cake Sentosa", email="sentosa.bakery@example.com", phone="021-5551234"),
            Business(id=b_ids[1], name="Green Grocer Indonesia", email="info@greengrocer.example.com", phone="021-5555678"),
            Business(id=b_ids[2], name="Mpok Siti Catering", email="mpoksiti@example.com", phone="0812-88889999")
        ]
        session.add_all(businesses)

        # 2. Seed Stores
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

        # 3. Seed Wallets
        wallets = [
            Wallet(id=w_ids[0], store_id=s_ids[0], balance=0),
            Wallet(id=w_ids[1], store_id=s_ids[1], balance=0),
            Wallet(id=w_ids[2], store_id=s_ids[2], balance=0)
        ]
        session.add_all(wallets)

        await session.flush()
        logger.info(f"Successfully seeded {len(businesses)} businesses, {len(stores)} stores, and {len(wallets)} wallets.")

        return b_ids, s_ids, w_ids
