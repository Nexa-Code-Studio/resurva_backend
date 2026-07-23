import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_health():
    """Verify that root online status endpoint is running."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


@pytest.mark.anyio
async def test_complete_flow():
    """
    Test complete lifecycle flow using AsyncClient:
    1. Create Business
    2. Register User (Owner and Customer)
    3. Login (Get JWT Token)
    4. Create Store (and automatic Wallet verification)
    5. Create Product
    6. Place Order (authenticating with JWT token, verifying stock deduction & pricing)
    7. File upload via Storage Service
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]
        business_email = f"info_{unique_suffix}@resurvafoods.com"
        owner_username = f"owner_{unique_suffix}"
        owner_email = f"owner_{unique_suffix}@resurvafoods.com"
        customer_username = f"buyer_{unique_suffix}"
        customer_email = f"buyer_{unique_suffix}@email.com"

        # 1. Create Business
        business_payload = {
            "name": "Resurva Foods Co",
            "email": business_email,
            "phone": "0812345678"
        }
        resp = await ac.post("/api/v1/businesses/", json=business_payload)
        assert resp.status_code == 201, resp.text
        business_data = resp.json()
        business_id = business_data["id"]
        assert business_data["name"] == "Resurva Foods Co"

        # 2. Register Owner User
        owner_payload = {
            "username": owner_username,
            "email": owner_email,
            "password": "securepassword123",
            "role": "owner",
            "business_id": business_id
        }
        resp = await ac.post("/api/v1/auth/register", json=owner_payload)
        assert resp.status_code == 201, resp.text

        # 3. Register Customer User
        customer_payload = {
            "username": customer_username,
            "email": customer_email,
            "password": "buyersecure123",
            "role": "customer"
        }
        resp = await ac.post("/api/v1/auth/register", json=customer_payload)
        assert resp.status_code == 201, resp.text

        # 4. Login Customer (Get Access Token)
        login_payload = {
            "username_or_email": customer_username,
            "password": "buyersecure123"
        }
        resp = await ac.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200, resp.text
        login_data = resp.json()
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 5. Create Store under Business
        store_payload = {
            "name": "Resurva Supermart",
            "address": "123 Green Boulevard",
            "city": "Bandung",
            "longitude": 107.61,
            "latitude": -6.91,
            "business_id": business_id,
            "is_active": True
        }
        resp = await ac.post("/api/v1/stores/", json=store_payload)
        assert resp.status_code == 201, resp.text
        store_data = resp.json()
        store_id = store_data["id"]

        # 6. Verify Store Wallet was automatically created
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["balance"] == 0

        # 7. Create Product under Store
        product_payload = {
            "name": "Chocolate Donuts 6-Pack",
            "description": "Delicious donuts from this morning",
            "original_price": 60000,
            "discounted_price": 24000,
            "stock": 10,
            "product_type": "bakery",
            "expired_at": "2026-06-12T18:00:00Z",
            "store_id": store_id
        }
        resp = await ac.post("/api/v1/products/", json=product_payload)
        assert resp.status_code == 201, resp.text
        product_data = resp.json()
        product_id = product_data["id"]

        # 8. Place Order using Customer Auth Token
        order_payload = {
            "store_id": store_id,
            "channel": "marketplace",
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 3
                }
            ]
        }
        resp = await ac.post("/api/v1/orders/", headers=headers, json=order_payload)
        assert resp.status_code == 201, resp.text
        order_data = resp.json()
        assert order_data["total_price"] == 180000  # 3 * 60,000 original
        assert order_data["total_discount"] == 108000  # 3 * (60,000 - 24,000)
        assert order_data["final_price"] == 72000  # 3 * 24,000 discounted
        assert len(order_data["order_items"]) == 1
        assert "daily_code" in order_data
        assert order_data["daily_code"] is not None
        assert "-" in order_data["daily_code"]
        assert order_data["store_latitude"] == -6.91
        assert order_data["store_longitude"] == 107.61

        # 9. Verify Product stock was reduced
        resp = await ac.get(f"/api/v1/products/{product_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["stock"] == 7  # 10 - 3 = 7

        # 10. Test upload file endpoint using Storage Provider
        file_payload = {"file": ("donut_image.png", b"fakedonutimagepngbytes", "image/png")}
        resp = await ac.post("/api/v1/products/upload-image", files=file_payload)
        assert resp.status_code == 200, resp.text
        upload_data = resp.json()
        assert "access_url" in upload_data
        assert upload_data["filename"] == "donut_image.png"

        # 11. Test store update including description, banner_url, and coordinates
        update_payload = {
            "description": "Premium store with fresh foods",
            "banner_url": "http://localhost:8080/uploads/stores/banner.png",
            "latitude": -7.95,
            "longitude": 112.62
        }
        resp = await ac.put(f"/api/v1/stores/{store_id}", json=update_payload)
        assert resp.status_code == 200, resp.text
        updated_data = resp.json()
        assert updated_data["description"] == "Premium store with fresh foods"
        assert updated_data["banner_url"] == "http://localhost:8080/uploads/stores/banner.png"
        assert updated_data["latitude"] == -7.95
        assert updated_data["longitude"] == 112.62

        # 12. Test creating enterprise request for store
        req_payload = {
            "corporate_name": "UMKM Berkah Group",
            "pic_name": "John Doe",
            "email": "corp@example.com",
            "phone": "08123456789"
        }
        resp = await ac.post(f"/api/v1/stores/{store_id}/enterprise-requests", json=req_payload)
        assert resp.status_code == 201, resp.text
        req_data = resp.json()
        assert req_data["corporate_name"] == "UMKM Berkah Group"
        assert req_data["pic_name"] == "John Doe"
        assert req_data["email"] == "corp@example.com"
        assert req_data["phone"] == "08123456789"
        assert req_data["status"] == "PENDING"

