import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio


async def test_superadmin_dashboard_stats():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/api/v1/analytics/superadmin/stats")
        assert res.status_code == 200, res.text
        data = res.json()
        
        # Verify schema structure
        assert "total_saved_kg" in data
        assert "total_co2_saved_kg" in data
        assert "total_transactions" in data
        assert "total_customers" in data
        assert "total_partners" in data
        assert "global_gmv" in data
        assert "pending_merchant_verifications" in data
        assert "pending_enterprise_verifications" in data

        # Check types
        assert isinstance(data["total_saved_kg"], (int, float))
        assert isinstance(data["total_co2_saved_kg"], (int, float))
        assert isinstance(data["total_transactions"], int)
        assert isinstance(data["total_customers"], int)
        assert isinstance(data["total_partners"], int)
        assert isinstance(data["global_gmv"], (int, float))
