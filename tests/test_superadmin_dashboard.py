import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio


async def test_superadmin_dashboard_stats():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Test default stats
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
        assert "trends" in data

        # Check types
        assert isinstance(data["total_saved_kg"], (int, float))
        assert isinstance(data["total_co2_saved_kg"], (int, float))
        assert isinstance(data["total_transactions"], int)
        assert isinstance(data["total_customers"], int)
        assert isinstance(data["total_partners"], int)
        assert isinstance(data["global_gmv"], (int, float))
        assert isinstance(data["trends"], list)
        if len(data["trends"]) > 0:
            trend_item = data["trends"][0]
            assert "month" in trend_item
            assert "saved_kg" in trend_item
            assert "co2_saved_kg" in trend_item
            assert "transactions" in trend_item
            assert "gmv" in trend_item

        # Test cities list endpoint
        res_cities = await client.get("/api/v1/analytics/superadmin/cities")
        assert res_cities.status_code == 200, res_cities.text
        cities = res_cities.json()
        assert isinstance(cities, list)

        # Test stats with query parameters
        res_filtered = await client.get("/api/v1/analytics/superadmin/stats?timeframe=7d&city=Malang")
        assert res_filtered.status_code == 200, res_filtered.text
        data_filtered = res_filtered.json()
        assert "total_saved_kg" in data_filtered
        assert "trends" in data_filtered

        # Test superadmin AI insights endpoint
        res_ai = await client.get("/api/v1/analytics/superadmin/ai-insights")
        assert res_ai.status_code == 200, res_ai.text
        data_ai = res_ai.json()
        assert "recommendation" in data_ai
        assert isinstance(data_ai["recommendation"], str)


