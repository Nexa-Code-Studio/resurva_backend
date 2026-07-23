import logging
import random
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import UserRole
from app.core.security import get_password_hash
from app.modules.users.models import User

logger = logging.getLogger("app.db.seeders.user")


class UserSeeder:
    @staticmethod
    async def seed(
        session: AsyncSession,
        business_ids: list[uuid.UUID],
        store_ids: list[uuid.UUID]
    ) -> dict[str, list[uuid.UUID]]:
        """
        Seeds the database with various types of users:
        - 1 Admin
        - 5 Owners (linked to businesses)
        - 50 Sellers (linked to businesses and specific stores)
        - 50 Customers
        
        Returns a dictionary mapping role names to lists of generated user UUIDs.
        """
        logger.info("Seeding users...")
        hashed_password = get_password_hash("password123")

        # 1. Pre-generate UUIDs
        admin_ids = [uuid.uuid4()]
        owner_ids = [uuid.uuid4() for _ in range(len(business_ids))]
        seller_ids = [uuid.uuid4() for _ in range(len(store_ids))]
        customer_ids = [uuid.uuid4() for _ in range(50)]

        users = []

        # 2. Seed Admin
        users.append(
            User(
                id=admin_ids[0],
                username="super_admin",
                email="admin@resurva.com",
                password=hashed_password,
                role=UserRole.ADMIN
            )
        )

        # 3. Seed Owners
        for idx, b_id in enumerate(business_ids):
            users.append(User(
                id=owner_ids[idx],
                business_id=b_id,
                username=f"owner_business_{idx + 1}",
                email=f"owner_biz{idx + 1}@resurva.com",
                password=hashed_password,
                role=UserRole.OWNER
            ))

        # 4. Seed Sellers — 1 per store, linked to correct store and business
        for idx, st_id in enumerate(store_ids):
            b_id = business_ids[idx // 10] if (idx // 10) < len(business_ids) else business_ids[-1]
            users.append(User(
                id=seller_ids[idx],
                business_id=b_id,
                store_id=st_id,
                username=f"seller_store_{idx + 1}",
                email=f"seller_store{idx + 1}@resurva.com",
                password=hashed_password,
                role=UserRole.SELLER
            ))

        # 5. Seed Customers (50 diverse entries)
        first_names = [
            "Budi", "Siti", "Ani", "Dodi", "Eka", "Rizky", "Dewi", "Agus", "Mega", "Hendra",
            "Yanto", "Rina", "Adit", "Fitri", "Tono", "Wati", "Andi", "Sri", "Joko", "Lilis"
        ]
        last_names = [
            "Sutrisno", "Aminah", "Lestari", "Hermawan", "Pratama", "Hidayat", "Sari", "Wibowo",
            "Putri", "Wijaya", "Kusuma", "Santoso", "Sitorus", "Siregar", "Ginting", "Nasution",
            "Lubis", "Pasaribu", "Pohan", "Simanjuntak"
        ]

        # Use local Random instance to preserve seed reproducibility
        local_random = random.Random(42)
        generated_usernames = set()

        _LAT_MIN = -7.577204
        _LAT_MAX = -7.541387
        _LNG_MIN = 110.832934
        _LNG_MAX = 110.879369

        for idx in range(50):
            while True:
                f_name = local_random.choice(first_names)
                l_name = local_random.choice(last_names)
                username = f"{f_name.lower()}_{l_name.lower()}_{local_random.randint(10, 99)}"
                if username not in generated_usernames:
                    generated_usernames.add(username)
                    break

            lat = round(local_random.uniform(_LAT_MIN, _LAT_MAX), 6)
            lng = round(local_random.uniform(_LNG_MIN, _LNG_MAX), 6)
            address = f"Jl. Slamet Riyadi No. {idx + 100}, Surakarta"
            phone = f"+628123456{idx:03d}"
            full_name = f"{f_name} {l_name}"

            users.append(User(
                id=customer_ids[idx],
                username=username,
                email=f"{username}@example.com",
                password=hashed_password,
                role=UserRole.CUSTOMER,
                full_name=full_name,
                phone_number=phone,
                default_address=address,
                default_latitude=lat,
                default_longitude=lng
            ))

        # 6. Add all to session
        session.add_all(users)
        await session.flush()
        logger.info(f"Successfully seeded {len(users)} users.")

        return {
            "admins": admin_ids,
            "owners": owner_ids,
            "sellers": seller_ids,
            "customers": customer_ids
        }
