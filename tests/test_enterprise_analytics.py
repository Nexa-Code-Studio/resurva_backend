import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal
from app.modules.business.models import Business
from app.modules.stores.models import Store, StoreCategory

pytestmark = pytest.mark.asyncio

async def test_enterprise_waste_impact_analytics_flow():
    b_id = uuid.uuid4()
    async with SessionLocal() as db:
        bus = Business(id=b_id, name=f"Analytics Corp {b_id.hex[:8]}", email=f"an_{b_id.hex[:8]}@corp.com", phone="081234567")
        db.add(bus)
        
        cat = StoreCategory(id=uuid.uuid4(), name=f"AnCat_{b_id.hex[:6]}")
        db.add(cat)
        await db.flush()

        s1 = Store(id=uuid.uuid4(), business_id=b_id, name="Analytics Branch A", address="Jl A 1", city="Malang", category_id=cat.id, longitude=112.6, latitude=-7.9)
        db.add(s1)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/api/v1/analytics/enterprise/waste-impact?business_id={b_id}")
        assert res.status_code == 200, res.text
        data = res.json()
        assert "financial_loss_avoided" in data
        assert "food_saved_kg" in data
        assert "co2e_reduced_kg" in data
        assert "branch_comparison" in data
        assert "emission_trend" in data
