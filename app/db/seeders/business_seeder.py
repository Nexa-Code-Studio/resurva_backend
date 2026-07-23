import os
import shutil
import logging
import random
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.business.models import Business
from app.modules.stores.models import Store, StoreCategory
from app.core.enums import WalletType
from app.modules.wallets.models import Wallet

logger = logging.getLogger("app.db.seeders.business")

# Bounding box area Surakarta dari koordinat yang diberikan pengguna
_LAT_MIN = -7.577204
_LAT_MAX = -7.541387
_LNG_MIN = 110.832934
_LNG_MAX = 110.879369

_rng = random.Random(99)

def _rand_lat() -> float:
    return round(_rng.uniform(_LAT_MIN, _LAT_MAX), 6)

def _rand_lng() -> float:
    return round(_rng.uniform(_LNG_MIN, _LNG_MAX), 6)


class BusinessSeeder:
    @staticmethod
    async def seed(session: AsyncSession) -> tuple[list[uuid.UUID], list[uuid.UUID], list[uuid.UUID]]:
        """
        Seeds 5 businesses (prototype enterprises) with 10 stores each (total 50 stores)
        inside the Malang bounding box and their wallets.
        Returns a tuple of (business_ids, store_ids, wallet_ids).
        """
        logger.info("Seeding 5 businesses, 50 stores, and wallets...")

        # Setup upload directories and copy default store images if they exist
        src_store_dir = "/home/mashupsoat/Project/resurva/uploads/default/store"
        dest_store_dir = "uploads/stores"
        os.makedirs(dest_store_dir, exist_ok=True)
        if os.path.exists(src_store_dir):
            for filename in os.listdir(src_store_dir):
                if filename.endswith(".png"):
                    shutil.copy(
                        os.path.join(src_store_dir, filename),
                        os.path.join(dest_store_dir, filename)
                    )

        business_configs = [
            ("Kopi & Roti Nusantara", "info@kopinusantara.com", "0341-111222"),
            ("Supermarket Segar Malang", "contact@segarmalang.com", "0341-333444"),
            ("Catering Mpok Siti Group", "order@mpoksitigroup.com", "0341-555666"),
            ("Horeca Depot Jatim", "support@horecadepot.com", "0341-777888"),
            ("Toko Roti & Kue Sentosa", "sentosacakes@sentosa.com", "0341-999000"),
        ]

        b_ids = []
        s_ids = []
        w_ids = []

        categories = ["Warung Makan", "Bakeri & Pastry", "Healthy Food", "Supermarket", "Coffee Shop"]
        pickup_windows = ["17:00 - 19:00 WIB", "16:00 - 18:00 WIB", "18:00 - 20:00 WIB", "19:00 - 21:00 WIB"]

        # Setup categories in database first
        cat_map = {}
        for cat_name in categories:
            cat_obj = StoreCategory(name=cat_name)
            session.add(cat_obj)
            cat_map[cat_name] = cat_obj
        await session.flush()

        for b_idx, (b_name, b_email, b_phone) in enumerate(business_configs):
            b_id = uuid.uuid4()
            b_ids.append(b_id)

            business = Business(
                id=b_id,
                name=b_name,
                email=b_email,
                phone=b_phone
            )
            session.add(business)

            # Create 10 stores for this business
            for s_idx in range(10):
                s_id = uuid.uuid4()
                s_ids.append(s_id)
                w_id = uuid.uuid4()
                w_ids.append(w_id)

                cat = _rng.choice(categories)
                p_win = _rng.choice(pickup_windows)

                # Assign image from 1.png to 8.png
                img_num = (s_idx % 8) + 1
                image_url = f"/uploads/stores/{img_num}.png"

                import json
                default_categories = ["Bakery", "Makanan Berat", "Minuman", "Makanan Kemasan", "Produk Segar", "Lainnya"]
                store = Store(
                    id=s_id,
                    business_id=b_id,
                    name=f"{b_name} - Cabang {s_idx + 1}",
                    address=f"Jl. Slamet Riyadi No. {b_idx * 10 + s_idx + 1}",
                    city="Surakarta",
                    rating=round(_rng.uniform(4.0, 5.0), 1),
                    is_active=True,
                    longitude=_rand_lng(),
                    latitude=_rand_lat(),
                    store_category=cat_map[cat],
                    pickup_time=p_win,
                    image_url=image_url,
                    categories_data=json.dumps(default_categories),
                    operating_hours="08:00 - 21:00"
                )
                session.add(store)

                digital_wallet = Wallet(
                    id=w_id,
                    store_id=s_id,
                    type=WalletType.DIGITAL,
                    balance=0
                )
                offline_wallet = Wallet(
                    id=uuid.uuid4(),
                    store_id=s_id,
                    type=WalletType.OFFLINE,
                    balance=0
                )
                session.add_all([digital_wallet, offline_wallet])

        await session.flush()
        logger.info(f"Successfully seeded {len(b_ids)} businesses, {len(s_ids)} stores, and wallets.")

        return b_ids, s_ids, w_ids
