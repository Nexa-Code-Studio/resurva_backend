import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal
from app.modules.business.models import Business
from app.modules.stores.models import Store, StoreCategory

pytestmark = pytest.mark.asyncio

async def test_enterprise_leaderboard_flow():
    b_id = uuid.uuid4()
    async with SessionLocal() as db:
        bus = Business(id=b_id, name=f"Leaderboard Group {b_id.hex[:8]}", email=f"corp_{b_id.hex[:8]}@lb.com", phone="0812345")
        db.add(bus)
        
        cat_name = f"Cat_{b_id.hex[:6]}"
        cat = StoreCategory(id=uuid.uuid4(), name=cat_name)
        db.add(cat)
        await db.flush()


        s1 = Store(id=uuid.uuid4(), business_id=b_id, name="Branch A", address="Addr 1", city="Jakarta", category_id=cat.id, longitude=112.616335, latitude=-7.940026)
        s2 = Store(id=uuid.uuid4(), business_id=b_id, name="Branch B", address="Addr 2", city="Surabaya", category_id=cat.id, longitude=112.738153, latitude=-7.260533)

        db.add_all([s1, s2])
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get(f"/api/v1/analytics/enterprise/leaderboard?business_id={b_id}&period=Bulan+Ini")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["period"] == "Bulan Ini"
        assert len(data["items"]) >= 2
        ranks = [item["rank"] for item in data["items"]]
        assert ranks == [1, 2]
