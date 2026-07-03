import os
import shutil
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

        # Copy product default images to serving uploads/products/
        src_prod_dir = "/home/mashupsoat/Project/resurva/uploads/default/product"
        dest_prod_dir = "uploads/products"
        os.makedirs(dest_prod_dir, exist_ok=True)
        if os.path.exists(src_prod_dir):
            for filename in os.listdir(src_prod_dir):
                if filename.endswith(".png"):
                    shutil.copy(
                        os.path.join(src_prod_dir, filename),
                        os.path.join(dest_prod_dir, filename)
                    )

        # 2. Define Product Templates
        bakery_templates = [
            ("Roti Tawar Gandum", ProductType.BAKERY, 20000, 10000, "Roti gandum utuh berserat tinggi.", 12),
            ("Croissant Cokelat", ProductType.BAKERY, 15000, 8000, "Croissant cokelat renyah bumbu mentega.", 8),
            ("Kue Sus Fla Vanila", ProductType.BAKERY, 8000, 4000, "Kue sus manis isi vanila segar.", 6),
            ("Brownies Panggang", ProductType.BAKERY, 65000, 35000, "Brownies panggang premium almond topping.", 24),
            ("Donat Kentang Gula", ProductType.BAKERY, 7000, 3500, "Donat kentang tradisional tabur gula pasir halus.", 8),
            ("Baguette Perancis", ProductType.BAKERY, 18000, 9000, "Roti baguette panjang renyah khas Perancis.", 12),
            ("Roti Keset Keju", ProductType.BAKERY, 25000, 15000, "Roti sobek lembut isi keju cheddar melimpah.", 12),
            ("Cinnamon Roll", ProductType.BAKERY, 16000, 10000, "Roti gulung aroma kayu manis dengan krim keju cair.", 10),
            ("Muffin Blueberry", ProductType.BAKERY, 12000, 7000, "Muffin blueberry manis dengan crumble renyah.", 8),
            ("Roti Abon Sapi", ProductType.BAKERY, 14000, 8000, "Roti manis lembut dengan taburan abon sapi gurih.", 8),
        ]

        produce_templates = [
            ("Sayur Bayam Organik", ProductType.PRODUCE, 12000, 5000, "Bayam segar hidroponik bebas pestisida.", 48),
            ("Susu UHT Full Cream 1L", ProductType.PACKAGED, 25000, 15000, "Susu UHT steril kemasan karton 1 liter.", 720),
            ("Daging Dada Ayam 500g", ProductType.PRODUCE, 38000, 22000, "Fillet dada ayam segar tanpa tulang.", 36),
            ("Tomat Ceri 250g", ProductType.PRODUCE, 18000, 9000, "Tomat ceri merah segar manis asam.", 48),
            ("Beras Pandan Wangi 5kg", ProductType.PACKAGED, 85000, 68000, "Beras pandan wangi pulen Cianjur asli.", 1440),
            ("Wortel Lokal 1kg", ProductType.PRODUCE, 15000, 8000, "Wortel lokal segar manis kaya vitamin A.", 72),
            ("Minyak Goreng 2L", ProductType.PACKAGED, 40000, 32000, "Minyak goreng kelapa sawit murni kemasan pouch.", 2160),
            ("Bawang Merah Kupas 250g", ProductType.PRODUCE, 20000, 12000, "Bawang merah kupas segar siap masak.", 96),
            ("Telur Ayam Negeri 10 Butir", ProductType.PRODUCE, 22000, 15000, "Telur ayam segar pilihan isi 10 butir.", 120),
            ("Kecap Manis Botol 275ml", ProductType.PACKAGED, 12000, 9000, "Kecap manis kental dari kedelai hitam pilihan.", 2880),
        ]

        ready_templates = [
            ("Nasi Rames Ayam Bakar", ProductType.READY_TO_EAT, 28000, 14000, "Nasi rames dengan lauk ayam bakar dan lalapan.", 6),
            ("Rendang Sapi Porsi", ProductType.READY_TO_EAT, 35000, 18000, "Rendang daging sapi bumbu Padang asli.", 12),
            ("Sayur Lodeh Betawi", ProductType.READY_TO_EAT, 15000, 7500, "Sayur lodeh kuah santan gurih melimpah.", 4),
            ("Tempe & Tahu Bacem", ProductType.READY_TO_EAT, 12000, 6000, "Tempe tahu bacem manis legit isi 4.", 8),
            ("Nasi Goreng Spesial", ProductType.READY_TO_EAT, 22000, 12000, "Nasi goreng kecap dengan telur dadar dan acar.", 6),
            ("Soto Ayam Lamongan", ProductType.READY_TO_EAT, 20000, 11000, "Soto ayam kuah kuning gurih koya melimpah.", 4),
            ("Gado-Gado Siram", ProductType.READY_TO_EAT, 18000, 10000, "Gado-gado sayuran segar dengan bumbu kacang kental.", 4),
            ("Ayam Goreng Lengkuas", ProductType.READY_TO_EAT, 25000, 14000, "Ayam goreng kremes lengkuas gurih isi 2 potong.", 8),
            ("Sambal Goreng Ati Ampela", ProductType.READY_TO_EAT, 16000, 9000, "Sambal goreng ati ampela kentang dadu pedas manis.", 8),
            ("Orek Tempe Basah", ProductType.READY_TO_EAT, 10000, 5000, "Tempe orek bumbu kecap manis gurih porsi keluarga.", 6),
        ]

        products = []
        local_random = random.Random(42)

        # Seed products for all stores
        for s_idx, store_id in enumerate(store_ids):
            # Alternate templates based on store index
            if s_idx % 3 == 0:
                templates = bakery_templates
            elif s_idx % 3 == 1:
                templates = produce_templates
            else:
                templates = ready_templates

            # Select 6 products from matching template
            chosen_templates = local_random.sample(templates, 6)
            for t_idx, (name, p_type, orig, disc, desc, exp_hours) in enumerate(chosen_templates):
                # Assign image_url from 1.png to 10.png
                img_num = (t_idx % 10) + 1
                image_url = f"/uploads/products/{img_num}.png"

                p = Product(
                    store_id=store_id,
                    name=name,
                    product_type=p_type,
                    original_price=orig,
                    discounted_price=disc,
                    description=desc,
                    stock=0,
                    sold=0,
                    image_url=image_url,
                    expiry_time=exp_hours,
                    expired_at=datetime.now(UTC) + timedelta(hours=exp_hours)
                )
                products.append(p)
                session.add(p)

        await session.flush()

        # 3. Link ProductIngredients
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
        discounts = []
        for s_idx, store_id in enumerate(store_ids):
            discounts.append(Discount(
                store_id=store_id,
                name=f"Voucher Hemat Cabang {s_idx + 1}",
                type=DiscountType.PERCENTAGE if s_idx % 2 == 0 else DiscountType.FIXED,
                value=20 if s_idx % 2 == 0 else 5000,
                quota=100000,
                code=f"HEMAT{s_idx + 1}",
                start_time=datetime.now(UTC) - timedelta(days=2000),
                end_time=datetime.now(UTC) + timedelta(days=2000)
            ))
            session.add(discounts[-1])

        await session.flush()
        logger.info(f"Successfully seeded {len(products)} products, {len(prod_ing_maps)} links, and {len(discounts)} discounts.")

        return products, ingredients_map, prod_ing_maps, discounts
