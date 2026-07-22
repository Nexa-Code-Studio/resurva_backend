import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_escrow_wallet_lifecycle():
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
            "name": "Escrow Test Foods Co",
            "email": business_email,
            "phone": "0812345678"
        }
        resp = await ac.post("/api/v1/businesses/", json=business_payload)
        assert resp.status_code == 201, resp.text
        business_data = resp.json()
        business_id = business_data["id"]

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
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 5. Create Store under Business
        store_payload = {
            "name": "Escrow Supermart",
            "address": "456 Escrow Boulevard",
            "city": "Malang",
            "longitude": 112.6326,
            "latitude": -7.9666,
            "business_id": business_id,
            "is_active": True
        }
        resp = await ac.post("/api/v1/stores/", json=store_payload)
        assert resp.status_code == 201, resp.text
        store_id = resp.json()["id"]

        # 6. Create Product under Store
        product_payload = {
            "name": "Escrow Bread",
            "description": "Tasty bread",
            "original_price": 50000,
            "discounted_price": 20000,
            "stock": 10,
            "product_type": "bakery",
            "expired_at": "2026-08-12T18:00:00Z",
            "store_id": store_id
        }
        resp = await ac.post("/api/v1/products/", json=product_payload)
        assert resp.status_code == 201, resp.text
        product_id = resp.json()["id"]

        # 7. Place Order (pending)
        order_payload = {
            "store_id": store_id,
            "channel": "marketplace",
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 2
                }
            ]
        }
        resp = await ac.post("/api/v1/orders/", headers=headers, json=order_payload)
        assert resp.status_code == 201, resp.text
        order_id = resp.json()["id"]
        assert resp.json()["status"] == "pending"

        # 8. Check Store Balances (escrow & wallets should be 0)
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances")
        assert resp.status_code == 200, resp.text
        assert resp.json()["digital"] == 0
        assert resp.json()["offline"] == 0
        assert resp.json()["escrow"] == 0

        # 9. Pay Order (status: paid)
        resp = await ac.put(f"/api/v1/orders/{order_id}/status", json={"status": "paid"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "paid"

        # 10. Check Store Balances after paid (escrow should have net amount: 40000 - 10% platform fee = 36000)
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances")
        assert resp.status_code == 200, resp.text
        assert resp.json()["digital"] == 0
        assert resp.json()["offline"] == 0
        assert resp.json()["escrow"] == 36000

        # 11. Transition to confirmed (disiapkan)
        resp = await ac.put(f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "confirmed"

        # Escrow should still be held
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances")
        assert resp.json()["escrow"] == 36000
        assert resp.json()["digital"] == 0

        # 12. Transition to prepared (siap diambil)
        resp = await ac.put(f"/api/v1/orders/{order_id}/status", json={"status": "prepared"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "prepared"

        # Escrow should still be held
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances")
        assert resp.json()["escrow"] == 36000
        assert resp.json()["digital"] == 0

        # 13. Transition to completed (selesai)
        resp = await ac.put(f"/api/v1/orders/{order_id}/status", json={"status": "completed"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"

        # Escrow should be released, digital wallet should get 36000
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances")
        assert resp.status_code == 200, resp.text
        assert resp.json()["digital"] == 36000
        assert resp.json()["escrow"] == 0
