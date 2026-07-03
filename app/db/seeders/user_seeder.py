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
        Seeds the database with various types of users for 1 enterprise:
        - 1 Admin
        - 1 Owner (linked to the single business)
        - 3 Sellers (one per store)
        - 50 Customers (all can transact across all 3 stores)

        Returns a dictionary mapping role names to lists of generated user UUIDs.
        """
        logger.info("Seeding users...")
        hashed_password = get_password_hash("password123")

        admin_ids = [uuid.uuid4()]
        owner_ids = [uuid.uuid4()]
        seller_ids = [uuid.uuid4() for _ in range(3)]
        customer_ids = [uuid.uuid4() for _ in range(50)]

        b_id = business_ids[0]
        users = []

        # 1. Admin
        users.append(User(
            id=admin_ids[0],
            username="super_admin",
            email="admin@resurva.com",
            password=hashed_password,
            role=UserRole.ADMIN
        ))

        # 2. Owner
        users.append(User(
            id=owner_ids[0],
            business_id=b_id,
            username="owner_warungmalang",
            email="owner@warungmalang.example.com",
            password=hashed_password,
            role=UserRole.OWNER
        ))

        # 3. Sellers — 1 per store
        seller_data = [
            ("seller_klojen",   "seller_klojen@warungmalang.example.com",   store_ids[0]),
            ("seller_blimbing", "seller_blimbing@warungmalang.example.com", store_ids[1]),
            ("seller_sukun",    "seller_sukun@warungmalang.example.com",    store_ids[2]),
        ]
        for idx, (uname, email, s_id) in enumerate(seller_data):
            users.append(User(
                id=seller_ids[idx],
                business_id=b_id,
                store_id=s_id,
                username=uname,
                email=email,
                password=hashed_password,
                role=UserRole.SELLER
            ))

        # 4. Customers — 50 diverse entries, all can shop at any store
        first_names = [
            "Budi", "Siti", "Ani", "Dodi", "Eka", "Rizky", "Dewi", "Agus", "Mega", "Hendra",
            "Yanto", "Rina", "Adit", "Fitri", "Tono", "Wati", "Andi", "Sri", "Joko", "Lilis"
        ]
        last_names = [
            "Sutrisno", "Aminah", "Lestari", "Hermawan", "Pratama", "Hidayat", "Sari", "Wibowo",
            "Putri", "Wijaya", "Kusuma", "Santoso", "Sitorus", "Siregar", "Ginting", "Nasution",
            "Lubis", "Pasaribu", "Pohan", "Simanjuntak"
        ]

        local_random = random.Random(42)
        generated_usernames = set()

        for idx in range(50):
            while True:
                f_name = local_random.choice(first_names)
                l_name = local_random.choice(last_names)
                username = f"{f_name.lower()}_{l_name.lower()}_{local_random.randint(10, 99)}"
                if username not in generated_usernames:
                    generated_usernames.add(username)
                    break

            users.append(User(
                id=customer_ids[idx],
                username=username,
                email=f"{username}@example.com",
                password=hashed_password,
                role=UserRole.CUSTOMER
            ))

        session.add_all(users)
        await session.flush()
        logger.info(f"Successfully seeded {len(users)} users.")

        return {
            "admins": admin_ids,
            "owners": owner_ids,
            "sellers": seller_ids,
            "customers": customer_ids
        }
