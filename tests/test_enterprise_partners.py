import pytest
import uuid
import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import SessionLocal
from app.modules.business.models import Business

pytestmark = pytest.mark.asyncio

async def test_enterprise_partners_flow():
    # 1. Setup Business in DB
    b_id = uuid.uuid4()
    b_name = f"Enterprise Group {b_id.hex[:8]}"
    async with SessionLocal() as db:
        bus = Business(id=b_id, name=b_name, email=f"corp_{b_id.hex[:8]}@partner.com", phone="0812345678")
        db.add(bus)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:

        # 2. Create Store with Merchant User Credentials
        store_payload = {
            "name": "Toko Roti Berkah Malang",
            "address": "Jl. Suhat No. 1",
            "city": "Malang",
            "longitude": 112.616335,
            "latitude": -7.940026,
            "business_id": str(b_id),
            "category": "Bakery",
            "username": f"seller_{b_id.hex[:8]}",
            "password": "InitialPassword123!",
            "email": f"berkah_{b_id.hex[:8]}@outlet.com",
            "contact": "081234567890"
        }
        res_create = await client.post("/api/v1/stores/", json=store_payload)
        assert res_create.status_code == 201, res_create.text
        created_store = res_create.json()
        store_id = created_store["id"]
        assert created_store["name"] == "Toko Roti Berkah Malang"
        assert created_store["email"] == f"berkah_{b_id.hex[:8]}@outlet.com"

        # 3. Test Merchant Login with Initial Credentials
        login_payload = {
            "username_or_email": f"seller_{b_id.hex[:8]}",
            "password": "InitialPassword123!"
        }
        res_login = await client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200, res_login.text
        login_data = res_login.json()
        assert "access_token" in login_data

        # 4. List Stores for Business
        res_list = await client.get(f"/api/v1/stores/?business_id={b_id}")
        assert res_list.status_code == 200, res_list.text
        stores_data = res_list.json()
        assert stores_data["pagination"]["total"] >= 1
        assert any(s["id"] == store_id for s in stores_data["items"])

        # 5. Reset Merchant Seller Password
        reset_payload = {
            "new_password": "NewSecretPassword456!"
        }
        res_reset = await client.post(f"/api/v1/stores/{store_id}/reset-seller-password", json=reset_payload)
        assert res_reset.status_code == 200, res_reset.text

        # 6. Test Merchant Login with NEW Password (wait 1 sec so refresh token timestamp differs)
        await asyncio.sleep(1)
        login_new_payload = {
            "username_or_email": f"seller_{b_id.hex[:8]}",
            "password": "NewSecretPassword456!"
        }
        res_login_new = await client.post("/api/v1/auth/login", json=login_new_payload)
        assert res_login_new.status_code == 200, res_login_new.text



        # 7. Soft Delete Store (Deactivate)
        res_del = await client.delete(f"/api/v1/stores/{store_id}")
        assert res_del.status_code == 204

        # 8. Verify Store is now inactive (is_active = False)
        res_get = await client.get(f"/api/v1/stores/{store_id}")
        assert res_get.status_code == 200
        assert res_get.json()["is_active"] is False
