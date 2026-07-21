import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal
from app.modules.verifications.models import PartnerVerification
from app.modules.business.models import Business
from app.modules.stores.models import Store
from app.modules.users.models import User

pytestmark = pytest.mark.asyncio


async def test_partner_verification_full_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        email_merchant = f"merchant_{uuid.uuid4().hex[:8]}@example.com"
        email_enterprise = f"enterprise_{uuid.uuid4().hex[:8]}@example.com"

        # 1. Create Merchant Verification Request
        merchant_payload = {
            "partner_type": "MERCHANT",
            "name": "Kopi Senja Utama",
            "owner_or_director": "Budi Santoso",
            "category": "Cafe",
            "address": "Jl. Kopi No. 5, Malang",
            "email": email_merchant,
            "phone": "081234567890",
            "documents": ["ktp.pdf", "nib.pdf"]
        }
        res_post = await client.post("/api/v1/verifications/", json=merchant_payload)
        assert res_post.status_code == 201, res_post.text
        m_data = res_post.json()
        assert m_data["status"] == "PENDING"
        assert m_data["partner_type"] == "MERCHANT"
        m_id = m_data["id"]

        # 2. List Pending Merchant Verifications
        res_list = await client.get("/api/v1/verifications/?partner_type=MERCHANT&status_filter=PENDING")
        assert res_list.status_code == 200, res_list.text
        items = res_list.json()
        assert any(item["id"] == m_id for item in items)

        # 3. Approve Merchant Verification Request
        res_approve = await client.patch(
            f"/api/v1/verifications/{m_id}/status",
            json={"status": "APPROVED"}
        )
        assert res_approve.status_code == 200, res_approve.text
        assert res_approve.json()["status"] == "APPROVED"

        # 4. Verify DB Provisioning for Approved Merchant
        async with SessionLocal() as db:
            # Check Business
            bus_res = await db.execute(select(Business).where(Business.email == email_merchant))
            bus = bus_res.scalar_one_or_none()
            assert bus is not None
            assert bus.pic == "Budi Santoso"

            # Check Store
            store_res = await db.execute(select(Store).where(Store.business_id == bus.id))
            store = store_res.scalar_one_or_none()
            assert store is not None
            assert store.name == "Kopi Senja Utama"

            # Check User
            user_res = await db.execute(select(User).where(User.store_id == store.id))
            user = user_res.scalar_one_or_none()
            assert user is not None
            assert user.role.value == "seller"

        # 5. Create Enterprise Verification Request
        enterprise_payload = {
            "partner_type": "ENTERPRISE",
            "name": "PT Rasa Nusantara Nusantara",
            "owner_or_director": "Anita Wijaya",
            "branch_count": 8,
            "address": "Gedung Perkantoran Sudirman Kav. 21",
            "email": email_enterprise,
            "phone": "087766554433",
            "documents": ["akta.pdf", "npwp.pdf"]
        }
        res_post_ent = await client.post("/api/v1/verifications/", json=enterprise_payload)
        assert res_post_ent.status_code == 201, res_post_ent.text
        ent_data = res_post_ent.json()
        ent_id = ent_data["id"]

        # 6. Reject Enterprise Verification Request
        res_reject = await client.patch(
            f"/api/v1/verifications/{ent_id}/status",
            json={"status": "REJECTED", "rejection_reason": "Dokumen Akta Pendirian kurang lengkap."}
        )
        assert res_reject.status_code == 200, res_reject.text
        rejected_data = res_reject.json()
        assert rejected_data["status"] == "REJECTED"
        assert rejected_data["rejection_reason"] == "Dokumen Akta Pendirian kurang lengkap."
