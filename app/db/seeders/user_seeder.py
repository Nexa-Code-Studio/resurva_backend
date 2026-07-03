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
        - 2 Admins
        - 3 Owners (linked to businesses)
        - 3 Sellers (linked to businesses and specific stores)
        - 50 Customers
        
        Returns a dictionary mapping role names to lists of generated user UUIDs.
        """
        logger.info("Seeding users...")
        hashed_password = get_password_hash("password123")

        # 1. Pre-generate UUIDs
        admin_ids = [uuid.uuid4() for _ in range(2)]
        owner_ids = [uuid.uuid4() for _ in range(3)]
        seller_ids = [uuid.uuid4() for _ in range(3)]
        customer_ids = [uuid.uuid4() for _ in range(50)]

        users = []

        # 2. Seed Admins
        users.extend([
            User(
                id=admin_ids[0],
                username="super_admin",
                email="admin@resurva.com",
                password=hashed_password,
                role=UserRole.ADMIN
            ),
            User(
                id=admin_ids[1],
                username="system_admin",
                email="sysadmin@resurva.com",
                password=hashed_password,
                role=UserRole.ADMIN
            )
        ])

        # 3. Seed Owners
        owner_usernames = ["owner_sentosa", "owner_green", "owner_mpoksiti"]
        owner_emails = ["owner_sentosa@example.com", "owner_green@example.com", "owner_mpoksiti@example.com"]
        for idx in range(3):
            # Fallback to random UUID if not enough business IDs provided
            biz_id = business_ids[idx] if idx < len(business_ids) else uuid.uuid4()
            users.append(User(
                id=owner_ids[idx],
                business_id=biz_id,
                username=owner_usernames[idx],
                email=owner_emails[idx],
                password=hashed_password,
                role=UserRole.OWNER
            ))

        # 4. Seed Sellers
        seller_usernames = ["seller_sentosa", "seller_green", "seller_mpoksiti"]
        seller_emails = ["seller_sentosa@example.com", "seller_green@example.com", "seller_mpoksiti@example.com"]
        for idx in range(3):
            biz_id = business_ids[idx] if idx < len(business_ids) else uuid.uuid4()
            st_id = store_ids[idx] if idx < len(store_ids) else uuid.uuid4()
            users.append(User(
                id=seller_ids[idx],
                business_id=biz_id,
                store_id=st_id,
                username=seller_usernames[idx],
                email=seller_emails[idx],
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

        # 6. Add all to session and flush to ensure database constraints hold
        session.add_all(users)
        await session.flush()
        logger.info(f"Successfully seeded {len(users)} users.")

        return {
            "admins": admin_ids,
            "owners": owner_ids,
            "sellers": seller_ids,
            "customers": customer_ids
        }
