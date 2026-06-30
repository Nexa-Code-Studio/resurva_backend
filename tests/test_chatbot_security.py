import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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

from app.core.enums import UserRole
from app.mcp.orchestrator import MCPOrchestrator
from app.db.session import SessionLocal


@pytest.mark.anyio
async def test_mcp_security_orchestrator_roles():
    """
    Test that MCPOrchestrator successfully filters and blocks execution
    based on UserRole constraints (e.g. seller accessing owner-only tools).
    """
    async with SessionLocal() as db:
        dummy_store_id = str(uuid.uuid4())

        # 1. Test Seller executing owner-only tool 'business_overview' - Should fail
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[dummy_store_id],
            name="business_overview",
            arguments={"business_id": str(uuid.uuid4())}
        )
        assert res["success"] is False
        assert "tidak diizinkan" in res["error"]

        # 2. Test Owner executing 'business_overview' - Should proceed to execution (will try to execute query, may return empty list or fail on query instead of authorization check)
        # We check that it didn't fail due to role checks
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.OWNER,
            allowed_store_ids=[dummy_store_id],
            name="business_overview",
            arguments={"business_id": str(uuid.uuid4())}
        )
        # It shouldn't fail due to "tidak diizinkan" role check
        if not res["success"]:
            assert "tidak diizinkan" not in res["error"]


@pytest.mark.anyio
async def test_mcp_security_store_isolation():
    """
    Test that MCPOrchestrator blocks a user (Seller/Owner) from accessing
    store details for stores not in their allowed list.
    """
    async with SessionLocal() as db:
        allowed_store = str(uuid.uuid4())
        forbidden_store = str(uuid.uuid4())

        # 1. Seller queries wallet for allowed store - Should succeed (or at least pass security guard)
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[allowed_store],
            name="check_wallet",
            arguments={"store_id": allowed_store}
        )
        # Should not fail due to access control
        if not res["success"]:
            assert "Akses ditolak" not in res["error"]

        # 2. Seller queries wallet for forbidden store - Should fail with Access Denied
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.SELLER,
            allowed_store_ids=[allowed_store],
            name="check_wallet",
            arguments={"store_id": forbidden_store}
        )
        assert res["success"] is False
        assert "Akses ditolak" in res["error"]

        # 3. Customer queries wallet (customer role is not in allowed_roles for check_wallet) - Should fail on role check
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.CUSTOMER,
            allowed_store_ids=[allowed_store],
            name="check_wallet",
            arguments={"store_id": allowed_store}
        )
        assert res["success"] is False
        assert "tidak diizinkan" in res["error"]


@pytest.mark.anyio
async def test_product_search_fuzzy_normalization():
    """
    Test that product_search MCP tool performs fuzzy matching and
    correctly returns confidence scores ordered by relevance.
    """
    async with SessionLocal() as db:
        # Search with a typo (rotii)
        res = await MCPOrchestrator.execute_tool(
            db=db,
            role=UserRole.CUSTOMER,
            allowed_store_ids=[],
            name="product_search",
            arguments={"query": "rotii", "limit": 5}
        )
        assert res["success"] is True
        results = res["data"]["results"]
        assert len(results) > 0
        
        # Verify confidence scores and sorting
        prev_confidence = 1.1
        for item in results:
            assert "confidence" in item
            assert 0.0 <= item["confidence"] <= 1.0
            # Ensure they are sorted descending by confidence
            assert item["confidence"] <= prev_confidence
            prev_confidence = item["confidence"]

        # The top result should be a variant of "Roti" (e.g. Roti Tawar Gandum) with a decent score
        assert any("Roti" in item["name"] and item["confidence"] > 0.5 for item in results)

