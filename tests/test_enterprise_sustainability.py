import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal
from app.modules.business.models import Business
from app.modules.stores.models import Store, StoreCategory

pytestmark = pytest.mark.asyncio

async def test_enterprise_sustainability_and_wrapped_flow():
    b_id = uuid.uuid4()
    async with SessionLocal() as db:
        bus = Business(id=b_id, name=f"Sust Corp {b_id.hex[:8]}", email=f"sust_{b_id.hex[:8]}@corp.com", phone="081234567")
        db.add(bus)
        
        cat = StoreCategory(id=uuid.uuid4(), name=f"SustCat_{b_id.hex[:6]}")
        db.add(cat)
        await db.flush()

        s1 = Store(id=uuid.uuid4(), business_id=b_id, name="Green Store A", address="Jl Green 1", city="Malang", category_id=cat.id, longitude=112.6, latitude=-7.9)
        db.add(s1)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Test Sustainability Endpoint
        res_sust = await client.get(f"/api/v1/analytics/enterprise/sustainability?business_id={b_id}&period=6bulan")
        assert res_sust.status_code == 200, res_sust.text
        data_sust = res_sust.json()
        assert "co2e_total" in data_sust
        assert "trees_equivalent" in data_sust
        assert "km_driven_equivalent" in data_sust
        assert "phone_hours_equivalent" in data_sust

        # Test Wrapped Endpoint
        res_wrap = await client.get(f"/api/v1/analytics/enterprise/wrapped?business_id={b_id}&year=2024")
        assert res_wrap.status_code == 200, res_wrap.text
        data_wrap = res_wrap.json()
        assert data_wrap["company_name"] == f"Sust Corp {b_id.hex[:8]}"
        assert "food_waste_saved" in data_wrap
        assert "total_branches" in data_wrap
