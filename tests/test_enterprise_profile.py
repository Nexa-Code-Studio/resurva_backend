import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal
from app.modules.business.models import Business

pytestmark = pytest.mark.asyncio

async def test_enterprise_profile_get_and_update_flow():
    b_id = uuid.uuid4()
    async with SessionLocal() as db:
        bus = Business(
            id=b_id,
            name=f"Enterprise {b_id.hex[:8]}",
            email=f"prof_{b_id.hex[:8]}@corp.com",
            phone="081298765432",
            address="Jl. Default No. 1",
            legal_entity="Perseroan Terbatas",
            pic="Default PIC",
            sdg_commitment="SDG 9 & 17",
            year_founded="2025",
            description="Default Description"
        )
        db.add(bus)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. GET Business Profile
        res_get = await client.get(f"/api/v1/business/{b_id}")
        assert res_get.status_code == 200, res_get.text
        data = res_get.json()
        assert data["name"] == f"Enterprise {b_id.hex[:8]}"
        assert data["legal_entity"] == "Perseroan Terbatas"

        # 2. PUT Update Business Profile
        update_payload = {
            "name": f"Updated Enterprise {b_id.hex[:8]}",
            "pic": "Ekya M. H. F.",
            "description": "Updated Corporate Description",
            "website": "https://resurva.id"
        }
        res_put = await client.put(f"/api/v1/business/{b_id}", json=update_payload)
        assert res_put.status_code == 200, res_put.text
        data_updated = res_put.json()
        assert data_updated["name"] == f"Updated Enterprise {b_id.hex[:8]}"
        assert data_updated["pic"] == "Ekya M. H. F."
        assert data_updated["website"] == "https://resurva.id"
