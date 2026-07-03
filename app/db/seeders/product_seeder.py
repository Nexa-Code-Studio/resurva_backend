import logging
import random
import uuid
from datetime import UTC, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import ProductType, DiscountType
from app.modules.products.models import Ingredient, Product, ProductIngredient
from app.modules.discounts.models import Discount

logger = logging.getLogger("app.db.seeders.product")

class ProductSeeder:
    @staticmethod
    async def seed(session: AsyncSession, store_ids: list[uuid.UUID]) -> tuple[list[Product], dict[str, Ingredient], list[ProductIngredient], list[Discount]]:
        """
        Seeds ingredients, products, product ingredients, and store discounts.
        Returns a tuple of (products, ingredients_map, prod_ing_maps, discounts).
        """
        logger.info("Seeding ingredients and products...")

        # 1. Seed Ingredients
        ing_configs = [
            ("Tepung Terigu", "gram", 0.0015),
            ("Mentega", "gram", 0.0080),
            ("Telur", "pcs", 0.3000),
            ("Gula Pasir", "gram", 0.0020),
            ("Cokelat Bubuk", "gram", 0.0120),
            ("Susu Cair", "ml", 0.0030),
            ("Sayur Bayam", "gram", 0.0005),
            ("Wortel", "gram", 0.0004),
            ("Tomat", "gram", 0.0008),
            ("Daging Ayam", "gram", 0.0069),
            ("Beras", "gram", 0.0025),
            ("Daging Sapi", "gram", 0.0270),
            ("Santan", "ml", 0.0022),
            ("Cabai", "gram", 0.0010),
            ("Tempe", "gram", 0.0009),
            ("Tahu", "gram", 0.0011),
            ("Plastik Kemasan", "pcs", 0.0500)
        ]
        ingredients_map = {}
        for name, unit, carbon in ing_configs:
            ing = Ingredient(name=name, unit=unit, carbon_per_unit=carbon)
            session.add(ing)
            ingredients_map[name] = ing

        await session.flush()

        # 2. Seed Products (30 items mapped to the store_ids)
        # We assume 3 stores. If store_ids length varies, fallback gracefully
        s1 = store_ids[0] if len(store_ids) > 0 else uuid.uuid4()
        s2 = store_ids[1] if len(store_ids) > 1 else uuid.uuid4()
        s3 = store_ids[2] if len(store_ids) > 2 else uuid.uuid4()

        p_configs = [
            # Store 1 - Sentosa Bakery
            (s1, "Roti Tawar Gandum", ProductType.BAKERY, 20000, 10000, "Roti gandum utuh berserat tinggi."),
            (s1, "Croissant Cokelat", ProductType.BAKERY, 15000, 8000, "Croissant cokelat renyah bumbu mentega."),
            (s1, "Kue Sus Fla Vanila", ProductType.BAKERY, 8000, 4000, "Kue sus manis isi vanila segar."),
            (s1, "Brownies Panggang", ProductType.BAKERY, 65000, 35000, "Brownies panggang premium almond topping."),
            (s1, "Donat Kentang Gula", ProductType.BAKERY, 7000, 3500, "Donat kentang tradisional tabur gula pasir halus."),
            (s1, "Baguette Perancis", ProductType.BAKERY, 18000, 9000, "Roti baguette panjang renyah khas Perancis."),
            (s1, "Roti Keset Keju", ProductType.BAKERY, 25000, 15000, "Roti sobek lembut isi keju cheddar melimpah."),
            (s1, "Cinnamon Roll", ProductType.BAKERY, 16000, 10000, "Roti gulung aroma kayu manis dengan krim keju cair."),
            (s1, "Muffin Blueberry", ProductType.BAKERY, 12000, 7000, "Muffin blueberry manis dengan crumble renyah."),
            (s1, "Roti Abon Sapi", ProductType.BAKERY, 14000, 8000, "Roti manis lembut dengan taburan abon sapi gurih."),

            # Store 2 - Green Grocer
            (s2, "Sayur Bayam Organik", ProductType.PRODUCE, 12000, 5000, "Bayam segar hidroponik bebas pestisida."),
            (s2, "Susu UHT Full Cream 1L", ProductType.PACKAGED, 25000, 15000, "Susu UHT steril kemasan karton 1 liter."),
            (s2, "Daging Dada Ayam 500g", ProductType.PRODUCE, 38000, 22000, "Fillet dada ayam segar tanpa tulang."),
            (s2, "Tomat Ceri 250g", ProductType.PRODUCE, 18000, 9000, "Tomat ceri merah segar manis asam."),
            (s2, "Beras Pandan Wangi 5kg", ProductType.PACKAGED, 85000, 68000, "Beras pandan wangi pulen Cianjur asli."),
            (s2, "Wortel Lokal 1kg", ProductType.PRODUCE, 15000, 8000, "Wortel lokal segar manis kaya vitamin A."),
            (s2, "Minyak Goreng 2L", ProductType.PACKAGED, 40000, 32000, "Minyak goreng kelapa sawit murni kemasan pouch."),
            (s2, "Bawang Merah Kupas 250g", ProductType.PRODUCE, 20000, 12000, "Bawang merah kupas segar siap masak."),
            (s2, "Telur Ayam Negeri 10 Butir", ProductType.PRODUCE, 22000, 15000, "Telur ayam segar pilihan isi 10 butir."),
            (s2, "Kecap Manis Botol 275ml", ProductType.PACKAGED, 12000, 9000, "Kecap manis kental dari kedelai hitam pilihan."),

            # Store 3 - Dapur Mpok Siti
            (s3, "Nasi Rames Ayam Bakar", ProductType.READY_TO_EAT, 28000, 14000, "Nasi rames dengan lauk ayam bakar dan lalapan."),
            (s3, "Rendang Sapi Porsi", ProductType.READY_TO_EAT, 35000, 18000, "Rendang daging sapi bumbu Padang asli."),
            (s3, "Sayur Lodeh Betawi", ProductType.READY_TO_EAT, 15000, 7500, "Sayur lodeh kuah santan gurih melimpah."),
            (s3, "Tempe & Tahu Bacem", ProductType.READY_TO_EAT, 12000, 6000, "Tempe tahu bacem manis legit isi 4."),
            (s3, "Nasi Goreng Spesial", ProductType.READY_TO_EAT, 22000, 12000, "Nasi goreng kecap dengan telur dadar dan acar."),
            (s3, "Soto Ayam Lamongan", ProductType.READY_TO_EAT, 20000, 11000, "Soto ayam kuah kuning gurih koya melimpah."),
            (s3, "Gado-Gado Siram", ProductType.READY_TO_EAT, 18000, 10000, "Gado-gado sayuran segar dengan bumbu kacang kental."),
            (s3, "Ayam Goreng Lengkuas", ProductType.READY_TO_EAT, 25000, 14000, "Ayam goreng kremes lengkuas gurih isi 2 potong."),
            (s3, "Sambal Goreng Ati Ampela", ProductType.READY_TO_EAT, 16000, 9000, "Sambal goreng ati ampela kentang dadu pedas manis."),
            (s3, "Orek Tempe Basah", ProductType.READY_TO_EAT, 10000, 5000, "Tempe orek bumbu kecap manis gurih porsi keluarga.")
        ]
        products = []
        for st_id, name, p_type, orig, disc, desc in p_configs:
            p = Product(
                store_id=st_id, name=name, product_type=p_type,
                original_price=orig, discounted_price=disc,
                description=desc, stock=0, sold=0,
                expired_at=datetime.now(UTC) + timedelta(days=2)
            )
            products.append(p)
            session.add(p)

        await session.flush()

        # 3. Link ProductIngredients (using local Random to ensure consistency)
        local_random = random.Random(42)
        prod_ing_maps = []
        for p in products:
            p_ings = local_random.sample(list(ingredients_map.keys()), local_random.randint(1, 3))
            for ing_name in p_ings:
                ing_obj = ingredients_map[ing_name]
                qty = local_random.uniform(10.0, 300.0) if ing_obj.unit != "pcs" else local_random.randint(1, 3)
                prod_ing_maps.append(ProductIngredient(
                    product_id=p.id,
                    ingredient_id=ing_obj.id,
                    quantity=round(qty, 2)
                ))
        session.add_all(prod_ing_maps)

        # 4. Seed Store Discounts
        discounts = [
            Discount(
                store_id=s1, name="Diskon Sore Bakery", type=DiscountType.PERCENTAGE, value=50, quota=100000,
                code="SOREBAKERY50", start_time=datetime.now(UTC) - timedelta(days=2000), end_time=datetime.now(UTC) + timedelta(days=2000)
            ),
            Discount(
                store_id=s2, name="Voucher Hemat Hijau", type=DiscountType.FIXED, value=5000, quota=100000,
                code="HEMAT5K", start_time=datetime.now(UTC) - timedelta(days=2000), end_time=datetime.now(UTC) + timedelta(days=2000), is_voucher=True
            ),
            Discount(
                store_id=s3, name="Diskon Makan Siang Siti", type=DiscountType.PERCENTAGE, value=30, quota=100000,
                code="SIANGSITI30", start_time=datetime.now(UTC) - timedelta(days=2000), end_time=datetime.now(UTC) + timedelta(days=2000)
            )
        ]
        session.add_all(discounts)

        await session.flush()
        logger.info(f"Successfully seeded {len(products)} products, {len(prod_ing_maps)} links, and {len(discounts)} discounts.")

        return products, ingredients_map, prod_ing_maps, discounts
