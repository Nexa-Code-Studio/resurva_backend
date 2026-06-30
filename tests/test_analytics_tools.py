import uuid
import pytest
import math
from datetime import datetime, timedelta, timezone, date, time
from sqlalchemy import select

# Import all models to ensure they are registered on Base.metadata before tests run
from app.db.base import Base
from app.modules.business.models import Business
from app.modules.users.models import User
from app.modules.stores.models import Store
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

from app.db.session import SessionLocal, engine
from app.core.redis import redis_pool
from app.core.enums import UserRole, OrderStatus, ProductType, PaymentMethod, TransactionStatus, ExpiryAlertStatus
from app.mcp.orchestrator import MCPOrchestrator


@pytest.fixture(autouse=True)
async def cleanup_connections():
    yield
    await engine.dispose()
    await redis_pool.disconnect()


@pytest.mark.anyio
async def test_analytics_tools_integration():
    """
    Integration test for StockRecommendationTool and ProductAuditTool.
    """
    async with SessionLocal() as db:
        unique_id = uuid.uuid4().hex[:6]

        # 1. Setup Business & Store
        business = Business(
            name=f"Test Business {unique_id}",
            email=f"biz_{unique_id}@resurva.com",
            phone="12345678"
        )
        db.add(business)
        await db.commit()
        await db.refresh(business)

        store = Store(
            name=f"Test Store {unique_id}",
            address="Street 1",
            city="Jakarta",
            longitude=106.8,
            latitude=-6.2,
            business_id=business.id,
            is_active=True
        )
        db.add(store)
        await db.commit()
        await db.refresh(store)

        # 2. Setup Customer
        customer = User(
            username=f"cust_{unique_id}",
            email=f"cust_{unique_id}@resurva.com",
            password="password123",
            role=UserRole.CUSTOMER
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

        # 3. Setup Products
        # Product 1: Croissant - stock = 10 (good sales, good rating, overstock score should be calculated)
        p1 = Product(
            store_id=store.id,
            name="Test Croissant",
            original_price=10000,
            discounted_price=8000,
            stock=10,
            product_type=ProductType.BAKERY,
            expired_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        # Product 2: Muffin - stock = 20 (zero sales, bad rating, should flag RETIRE)
        p2 = Product(
            store_id=store.id,
            name="Test Muffin",
            original_price=12000,
            discounted_price=9000,
            stock=20,
            product_type=ProductType.BAKERY,
            expired_at=datetime.now(timezone.utc) + timedelta(days=3)
        )
        db.add_all([p1, p2])
        await db.commit()
        await db.refresh(p1)
        await db.refresh(p2)

        # 4. Setup Orders (P1 sold 28 units over the last 14 days, averaging 2 units/day)
        # P2 has zero sales.
        for i in range(1, 15):
            order = Order(
                user_id=customer.id,
                store_id=store.id,
                total_price=20000,
                total_discount=0,
                final_price=20000,
                status=OrderStatus.COMPLETED,
                created_at=datetime.now(timezone.utc) - timedelta(days=i, hours=2)
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)

            order_item = OrderItem(
                order_id=order.id,
                product_id=p1.id,
                quantity=2,
                unit_price=10000,
                subtotal=20000
            )
            db.add(order_item)
            await db.commit()

        # 5. Setup Reviews
        # P1 rating is 4.0 (2 reviews: 3 & 5)
        # P2 rating is 1.0 (1 review: 1)
        rev1 = Review(store_id=store.id, product_id=p1.id, user_id=customer.id, description="Okay", rating=3)
        rev2 = Review(store_id=store.id, product_id=p1.id, user_id=customer.id, description="Great", rating=5)
        rev3 = Review(store_id=store.id, product_id=p2.id, user_id=customer.id, description="Horrible", rating=1)
        db.add_all([rev1, rev2, rev3])
        await db.commit()

        # ----------------------------------------------------
        # TEST A: Stock Recommendation Tool Execution
        # ----------------------------------------------------
        # We test forecasting for next Tuesday (weekday, multiplier 1.0)
        target_weekday = "2026-06-16"  # Tuesday
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="stock_recommendation",
            arguments={
                "store_id": str(store.id),
                "period_days": 14,
                "target_date": target_weekday,
                "weekend_multiplier": 1.5
            }
        )
        assert res["success"] is True
        data = res["data"]
        assert data["target_date"] == target_weekday
        assert data["is_weekend"] is False
        assert data["multiplier_applied"] == 1.0

        # Croissant (P1): 28 sold in 14 days => avg_daily_sales = 2.0. Demand forecast = ceil(2 * 1.0) = 2.
        # stock = 10. recommendation = max(0, 2 - 10) = 0.
        croissant_rec = next(r for r in data["recommendations"] if r["product_name"] == "Test Croissant")
        assert croissant_rec["daily_average_sales"] == 2.0
        assert croissant_rec["adjusted_demand_forecast"] == 2
        assert croissant_rec["recommendation"] == 0

        # Now test forecasting for next Saturday (weekend, multiplier 1.5)
        target_weekend = "2026-06-20"  # Saturday
        res_we = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="stock_recommendation",
            arguments={
                "store_id": str(store.id),
                "period_days": 14,
                "target_date": target_weekend,
                "weekend_multiplier": 1.5
            }
        )
        assert res_we["success"] is True
        data_we = res_we["data"]
        assert data_we["is_weekend"] is True
        assert data_we["multiplier_applied"] == 1.5
        croissant_we = next(r for r in data_we["recommendations"] if r["product_name"] == "Test Croissant")
        # Demand forecast = ceil(2.0 * 1.5) = 3. stock = 10 => recommendation = 0.
        assert croissant_we["adjusted_demand_forecast"] == 3

        # ----------------------------------------------------
        # TEST B: Product Audit Tool Execution
        # ----------------------------------------------------
        res_audit = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="product_audit",
            arguments={
                "store_id": str(store.id),
                "period_days": 30
            }
        )
        assert res_audit["success"] is True
        audit_data = res_audit["data"]
        assert len(audit_data["audits"]) == 2

        # P1 (Test Croissant):
        # - Sales Score: sold 28, max_sales is 28 => Sales_Score = 100
        # - Rating Score: avg rating 4.0 / 5 => Rating_Score = 80
        # - Efficiency Score: stock = 10, avg_daily = 28/30 = 0.9333.
        #   overstock_ratio = 10 / (0.9333 * 3) = 10 / 2.8 = 3.5714.
        #   efficiency_score = max(0, 100 - 3.5714 * 50) = 0.
        # - Overall Score: 100 * 0.4 + 80 * 0.3 + 0 * 0.3 = 40 + 24 + 0 = 64
        # - Status: OPTIMIZE (since 50 <= 64 < 70)
        p1_audit = next(a for a in audit_data["audits"] if a["product_name"] == "Test Croissant")
        assert p1_audit["sales_score"] == 100.0
        assert p1_audit["rating_score"] == 80.0
        assert p1_audit["efficiency_score"] == 0.0
        assert p1_audit["overall_score"] == 64.0
        assert p1_audit["status"] == "OPTIMIZE"

        # P2 (Test Muffin):
        # - Sales Score: sold 0 => Sales_Score = 0
        # - Rating Score: avg rating 1.0 / 5 => Rating_Score = 20
        # - Efficiency Score: stock = 20, avg_daily = 0 => sold=0 but stock > 0 => Efficiency_Score = 0
        # - Overall Score: 0 * 0.4 + 20 * 0.3 + 0 * 0.3 = 6.0
        # - Status: RETIRE (since 6.0 < 50)
        p2_audit = next(a for a in audit_data["audits"] if a["product_name"] == "Test Muffin")
        assert p2_audit["sales_score"] == 0.0
        assert p2_audit["rating_score"] == 20.0
        assert p2_audit["efficiency_score"] == 0.0
        assert p2_audit["overall_score"] == 6.0
        assert p2_audit["status"] == "RETIRE"

        # ----------------------------------------------------
        # TEST C: Security/isolation check
        # ----------------------------------------------------
        # Unauthorized store query should fail
        unauthorized_id = str(uuid.uuid4())
        res_sec = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[unauthorized_id],
            name="product_audit",
            arguments={
                "store_id": str(store.id),
                "period_days": 30
            }
        )
        assert res_sec["success"] is False
        assert "Akses ditolak" in res_sec["error"]


@pytest.mark.anyio
async def test_product_search_list_and_count():
    """
    Test listing, counting, and out-of-stock features of modified ProductSearchTool.
    """
    async with SessionLocal() as db:
        unique_id = uuid.uuid4().hex[:6]

        # 1. Setup Business & Store
        business = Business(
            name=f"Search Biz {unique_id}",
            email=f"search_{unique_id}@resurva.com",
            phone="87654321"
        )
        db.add(business)
        await db.commit()
        await db.refresh(business)

        store = Store(
            name=f"Search Store {unique_id}",
            address="Street 2",
            city="Bandung",
            longitude=107.6,
            latitude=-6.9,
            business_id=business.id,
            is_active=True
        )
        db.add(store)
        await db.commit()
        await db.refresh(store)

        # 2. Setup 3 Products: P1 (stock 10), P2 (stock 0), P3 (stock 5)
        p1 = Product(
            store_id=store.id,
            name="Roti Cokelat",
            original_price=5000,
            discounted_price=4000,
            stock=10,
            product_type=ProductType.BAKERY,
            expired_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        p2 = Product(
            store_id=store.id,
            name="Donat Keju",
            original_price=6000,
            discounted_price=5000,
            stock=0,  # OUT OF STOCK
            product_type=ProductType.BAKERY,
            expired_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        p3 = Product(
            store_id=store.id,
            name="Roti Susu",
            original_price=7000,
            discounted_price=6000,
            stock=5,
            product_type=ProductType.BAKERY,
            expired_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        db.add_all([p1, p2, p3])
        await db.commit()

        # 3. Test product search with empty query and include_out_of_stock=True
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="product_search",
            arguments={
                "store_id": str(store.id),
                "query": None,
                "include_out_of_stock": True
            }
        )
        assert res["success"] is True
        data = res["data"]
        assert data["total_count"] == 3
        names = {p["name"] for p in data["results"]}
        assert "Roti Cokelat" in names
        assert "Donat Keju" in names
        assert "Roti Susu" in names

        # 4. Test product search with empty query and include_out_of_stock=False
        res_in_stock = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="product_search",
            arguments={
                "store_id": str(store.id),
                "query": "",
                "include_out_of_stock": False
            }
        )
        assert res_in_stock["success"] is True
        data_in_stock = res_in_stock["data"]
        assert data_in_stock["total_count"] == 2
        names_in_stock = {p["name"] for p in data_in_stock["results"]}
        assert "Roti Cokelat" in names_in_stock
        assert "Roti Susu" in names_in_stock
        assert "Donat Keju" not in names_in_stock

        # 5. Test fuzzy searching
        res_fuzzy = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="product_search",
            arguments={
                "store_id": str(store.id),
                "query": "roti",
                "include_out_of_stock": True
            }
        )
        assert res_fuzzy["success"] is True
        data_fuzzy = res_fuzzy["data"]
        # Both "Roti Cokelat" and "Roti Susu" should match well
        assert any(p["name"] == "Roti Cokelat" and p["confidence"] >= 0.5 for p in data_fuzzy["results"])


@pytest.mark.anyio
async def test_orchestrator_self_correction():
    """
    Test that MCPOrchestrator intercepts badly formed arguments and returns a self-correction hint.
    """
    async with SessionLocal() as db:
        # Pass a badly formed string as store_id to product_audit
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=["not-a-valid-uuid"],
            name="product_audit",
            arguments={
                "store_id": "not-a-valid-uuid",
                "period_days": 30
            }
        )
        assert res["success"] is False
        assert any(k in res["error"] for k in ["PENTING: Nilai ID", "Argumen input"])


@pytest.mark.anyio
async def test_session_slots_redis():
    """
    Test that SessionService successfully gets, sets, and clears context variables in Redis.
    """
    from app.modules.chat.service.session_service import SessionService
    conv_id = uuid.uuid4()
    
    # Verify slots are empty initially
    slots = await SessionService.get_slots(conv_id)
    assert slots == {}
    
    # Set slots
    await SessionService.set_slots(conv_id, {"selected_product_id": "p-123", "selected_product_name": "Roti"})
    
    # Retrieve slots
    slots2 = await SessionService.get_slots(conv_id)
    assert slots2["selected_product_id"] == "p-123"
    assert slots2["selected_product_name"] == "Roti"
    
    # Clear slots
    await SessionService.clear_session(conv_id)
    slots3 = await SessionService.get_slots(conv_id)
    assert slots3 == {}


@pytest.mark.anyio
async def test_analytics_caching():
    """
    Test that product_audit check and retrieval of cached analytics results from Redis works.
    """
    from app.core.redis import get_redis_client
    async with SessionLocal() as db:
        store_id = str(uuid.uuid4())
        cache_key = f"cache:product_audit:{store_id}:all:30"
        
        # Manually seed Redis cache
        redis_client = await get_redis_client()
        import json
        cached_res = {
            "store_id": store_id,
            "period_days": 30,
            "audits": [{"product_name": "Cached Croissant", "overall_score": 99.9}],
            "is_cached": True
        }
        await redis_client.set(cache_key, json.dumps(cached_res), ex=30)
        
        # Query product_audit tool - should hit cache
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[store_id],
            name="product_audit",
            arguments={
                "store_id": store_id,
                "period_days": 30
            }
        )
        assert res["success"] is True
        assert res["data"].get("is_cached") is True
        assert res["data"]["audits"][0]["product_name"] == "Cached Croissant"
        
        # Cleanup
        await redis_client.delete(cache_key)


@pytest.mark.anyio
async def test_upgraded_mcp_tools():
    """
    Test the upgraded MCP tools:
    - reviews_summary: product_id filter and created_at timestamps.
    - check_wallet: transaction_type filter, customizable limit, and status joining.
    - sales_summary: period='range' with start_date/end_date, platform fee, and refund calculations.
    - expiry_alerts: returning nested batch details and pricing.
    """
    async with SessionLocal() as db:
        unique_id = uuid.uuid4().hex[:6]

        # 1. Setup Business & Store
        business = Business(
            name=f"Upgraded Biz {unique_id}",
            email=f"upbiz_{unique_id}@resurva.com",
            phone="12345"
        )
        db.add(business)
        await db.commit()
        await db.refresh(business)

        store = Store(
            name=f"Upgraded Store {unique_id}",
            address="Street 3",
            city="Surabaya",
            longitude=112.7,
            latitude=-7.2,
            business_id=business.id,
            is_active=True
        )
        db.add(store)
        await db.commit()
        await db.refresh(store)

        # 2. Setup Customer & Products
        customer = User(
            username=f"cust2_{unique_id}",
            email=f"cust2_{unique_id}@resurva.com",
            password="password123",
            role=UserRole.CUSTOMER
        )
        p1 = Product(
            store_id=store.id,
            name="Upgraded Bread",
            original_price=10000,
            discounted_price=7000,
            stock=50,
            product_type=ProductType.BAKERY,
            expired_at=datetime.now(timezone.utc) + timedelta(days=5)
        )
        db.add_all([customer, p1])
        await db.commit()
        await db.refresh(customer)
        await db.refresh(p1)

        # 3. Setup Reviews
        rev = Review(
            store_id=store.id,
            product_id=p1.id,
            user_id=customer.id,
            description="Tastes amazing!",
            rating=5,
            created_at=datetime.now(timezone.utc)
        )
        db.add(rev)
        await db.commit()

        # 4. Setup Wallet & Transactions
        wallet = Wallet(store_id=store.id, balance=1000000)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

        # Order & Transaction (Success with Platform Fee)
        order = Order(
            user_id=customer.id,
            store_id=store.id,
            total_price=20000,
            total_discount=0,
            final_price=20000,
            status=OrderStatus.COMPLETED,
            created_at=datetime.now(timezone.utc)
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        tx_success = Transaction(
            order_id=order.id,
            store_id=store.id,
            gross_amount=20000,
            platform_fee=2000,
            net_amount=18000,
            payment_method=PaymentMethod.QRIS,
            status=TransactionStatus.SUCCESS,
            paid_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db.add(tx_success)
        await db.commit()
        await db.refresh(tx_success)

        # Wallet Transaction for Success (Credit)
        wtx_credit = WalletTransaction(
            wallet_id=wallet.id,
            transaction_id=tx_success.id,
            type=WalletTransactionType.CREDIT,
            amount=18000,
            balance_after=1018000,
            note="Kredit Penjualan",
            created_at=datetime.now(timezone.utc)
        )
        
        # Wallet Transaction for Withdrawal (Pending/Success status via joining Transaction)
        tx_withdrawal = Transaction(
            order_id=order.id,
            store_id=store.id,
            gross_amount=50000,
            platform_fee=0,
            net_amount=50000,
            payment_method=PaymentMethod.TRANSFER,
            status=TransactionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        db.add(tx_withdrawal)
        await db.commit()
        await db.refresh(tx_withdrawal)

        wtx_withdrawal = WalletTransaction(
            wallet_id=wallet.id,
            transaction_id=tx_withdrawal.id,
            type=WalletTransactionType.WITHDRAWAL,
            amount=-50000,
            balance_after=968000,
            note="Withdrawal to Bank",
            created_at=datetime.now(timezone.utc)
        )
        db.add_all([wtx_credit, wtx_withdrawal])
        await db.commit()

        # 5. Setup Expiry Alert & Inventory Batch
        batch = InventoryBatch(
            product_id=p1.id,
            store_id=store.id,
            quantity=50,
            remaining_quantity=35,
            expired_at=datetime.now(timezone.utc) + timedelta(days=2)
        )
        from app.core.enums import ExpiryAlertStatus
        alert = ExpiryAlert(
            product_id=p1.id,
            store_id=store.id,
            days_until_expiry=2,
            status=ExpiryAlertStatus.CRITICAL,
            alerted_at=datetime.now(timezone.utc)
        )
        db.add_all([batch, alert])
        await db.commit()

        # 6. Setup Daily Summary (needed for range query)
        ds = DailySummary(
            store_id=store.id,
            summary_date=date.today(),
            total_orders=1,
            total_revenue=20000,
            total_discount_given=0,
            items_sold=2,
            carbon_saved_kg=1.5,
            expiry_alerts_count=1
        )
        db.add(ds)
        await db.commit()

        # ----------------------------------------------------
        # TEST 1: reviews_summary with product_id filter
        # ----------------------------------------------------
        res_reviews = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="reviews_summary",
            arguments={
                "store_id": str(store.id),
                "product_id": str(p1.id),
                "limit": 5
            }
        )
        assert res_reviews["success"] is True
        rev_data = res_reviews["data"]
        assert rev_data["product_id"] == str(p1.id)
        assert len(rev_data["recent_reviews"]) == 1
        assert rev_data["recent_reviews"][0]["snippet"] == "Tastes amazing!"
        assert "created_at" in rev_data["recent_reviews"][0]

        # ----------------------------------------------------
        # TEST 2: check_wallet with transaction_type & status
        # ----------------------------------------------------
        from app.core.enums import WalletTransactionType
        res_wallet = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="check_wallet",
            arguments={
                "store_id": str(store.id),
                "include_transactions": True,
                "transaction_type": "withdrawal",
                "limit": 5
            }
        )
        assert res_wallet["success"] is True
        w_data = res_wallet["data"]
        assert len(w_data["recent_transactions"]) == 1
        assert w_data["recent_transactions"][0]["type"] == "withdrawal"
        assert w_data["recent_transactions"][0]["status"] == "pending"

        # ----------------------------------------------------
        # TEST 3: sales_summary with custom date range
        # ----------------------------------------------------
        today_str = date.today().isoformat()
        res_sales = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="sales_summary",
            arguments={
                "store_id": str(store.id),
                "period": "range",
                "start_date": today_str,
                "end_date": today_str
            }
        )
        assert res_sales["success"] is True
        sales_data = res_sales["data"]
        assert sales_data["total_orders"] == 1
        assert sales_data["total_revenue"] == 20000
        assert sales_data["total_platform_fee"] == 2000
        assert sales_data["total_refunded_amount"] == 0

        # ----------------------------------------------------
        # TEST 4: expiry_alerts returning nested batch and pricing
        # ----------------------------------------------------
        res_expiry = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[str(store.id)],
            name="expiry_alerts",
            arguments={
                "store_id": str(store.id),
                "critical_only": True
            }
        )
        assert res_expiry["success"] is True
        expiry_data = res_expiry["data"]
        assert len(expiry_data["alerts"]) == 1
        alert_item = expiry_data["alerts"][0]
        assert alert_item["product_id"] == str(p1.id)
        assert alert_item["original_price"] == 10000
        assert alert_item["discounted_price"] == 7000
        assert len(alert_item["batches"]) == 1
        assert alert_item["batches"][0]["remaining_quantity"] == 35



