import logging
import random
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.business.models import Business
from app.modules.stores.models import Store
from app.modules.wallets.models import Wallet

logger = logging.getLogger("app.db.seeders.business")

# Bounding box area Malang dari koordinat yang diberikan pengguna
_LAT_MIN = -7.984444
_LAT_MAX = -7.857874
_LNG_MIN = 112.501505
_LNG_MAX = 112.645326

_rng = random.Random(99)

def _rand_lat() -> float:
    return round(_rng.uniform(_LAT_MIN, _LAT_MAX), 6)

def _rand_lng() -> float:
    return round(_rng.uniform(_LNG_MIN, _LNG_MAX), 6)


class BusinessSeeder:
    @staticmethod
    async def seed(session: AsyncSession) -> tuple[list[uuid.UUID], list[uuid.UUID], list[uuid.UUID]]:
        """
        Seeds 1 business (prototype enterprise) with 3 stores inside the
        Malang bounding box and their wallets.
        Returns a tuple of (business_ids, store_ids, wallet_ids).
        """
        logger.info("Seeding business, stores, and wallets...")

        b_id = uuid.uuid4()
        s_ids = [uuid.uuid4() for _ in range(3)]
        w_ids = [uuid.uuid4() for _ in range(3)]

        # 1. Seed Business
        business = Business(
            id=b_id,
            name="Warung Malang Group",
            email="info@warungmalang.example.com",
            phone="0341-889900"
        )
        session.add(business)

        # 2. Seed 3 Stores — koordinat acak di dalam bounding box Malang
        stores = [
            Store(
                id=s_ids[0], business_id=b_id,
                name="Warung Malang - Cabang Klojen",
                address="Jl. Klojen Raya No. 10", city="Malang", rating=4.8,
                is_active=True,
                longitude=_rand_lng(), latitude=_rand_lat(),
                category="Warung Makan",
                pickup_time="17:00 - 19:00 WIB"
            ),
            Store(
                id=s_ids[1], business_id=b_id,
                name="Warung Malang - Cabang Blimbing",
                address="Jl. Blimbing Indah No. 5", city="Malang", rating=4.5,
                is_active=True,
                longitude=_rand_lng(), latitude=_rand_lat(),
                category="Bakeri & Pastry",
                pickup_time="16:00 - 18:00 WIB"
            ),
            Store(
                id=s_ids[2], business_id=b_id,
                name="Warung Malang - Cabang Sukun",
                address="Jl. Sukun Baru No. 22", city="Malang", rating=4.6,
                is_active=True,
                longitude=_rand_lng(), latitude=_rand_lat(),
                category="Healthy Food",
                pickup_time="18:00 - 20:00 WIB"
            ),
        ]
        session.add_all(stores)

        # 3. Seed Wallets
        wallets = [
            Wallet(id=w_ids[0], store_id=s_ids[0], balance=0),
            Wallet(id=w_ids[1], store_id=s_ids[1], balance=0),
            Wallet(id=w_ids[2], store_id=s_ids[2], balance=0),
        ]
        session.add_all(wallets)

        await session.flush()
        logger.info(f"Successfully seeded 1 business, {len(stores)} stores, and {len(wallets)} wallets.")

        return [b_id], s_ids, w_ids
