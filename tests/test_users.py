import pytest
import uuid
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.enums import UserRole

pytestmark = pytest.mark.asyncio


async def test_user_management_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        unique_username = f"admin_user_{uuid.uuid4().hex[:6]}"
        unique_email = f"admin_email_{uuid.uuid4().hex[:6]}@example.com"

        # 1. Create User
        create_payload = {
            "username": unique_username,
            "email": unique_email,
            "role": "admin",
            "password": "password123",
            "is_active": True
        }
        res_post = await client.post("/api/v1/users/", json=create_payload)
        assert res_post.status_code == 200, res_post.text
        user_data = res_post.json()
        assert user_data["username"] == unique_username
        assert user_data["email"] == unique_email
        assert user_data["role"] == "admin"
        assert user_data["is_active"] is True
        user_id = user_data["id"]

        # 2. Get User
        res_get = await client.get(f"/api/v1/users/{user_id}")
        assert res_get.status_code == 200, res_get.text
        assert res_get.json()["username"] == unique_username

        # 3. Update User (Change status to Suspended / inactive and role to seller)
        update_payload = {
            "role": "seller",
            "is_active": False
        }
        res_patch = await client.patch(f"/api/v1/users/{user_id}", json=update_payload)
        assert res_patch.status_code == 200, res_patch.text
        updated_data = res_patch.json()
        assert updated_data["role"] == "seller"
        assert updated_data["is_active"] is False

        # 4. List Users and verify filter
        res_list = await client.get("/api/v1/users/?role=seller")
        assert res_list.status_code == 200, res_list.text
        list_data = res_list.json()
        assert any(item["id"] == user_id for item in list_data["items"])

        # 5. Delete User
        res_del = await client.delete(f"/api/v1/users/{user_id}")
        assert res_del.status_code == 200, res_del.text
        assert res_del.json() == {"ok": True}

        # 6. Verify GET returns 404
        res_get_gone = await client.get(f"/api/v1/users/{user_id}")
        assert res_get_gone.status_code == 404, res_get_gone.text


async def test_user_profile_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        unique_username = f"buyer_{uuid.uuid4().hex[:6]}"
        unique_email = f"buyer_{uuid.uuid4().hex[:6]}@example.com"

        # 1. Register user
        register_payload = {
            "username": unique_username,
            "email": unique_email,
            "password": "buyersecure123",
            "role": "customer"
        }
        resp = await client.post("/api/v1/auth/register", json=register_payload)
        assert resp.status_code == 201, resp.text

        # 2. Login user to get token
        login_payload = {
            "username_or_email": unique_username,
            "password": "buyersecure123"
        }
        resp = await client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. GET /me (Verify initial/default values)
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200, resp.text
        me_data = resp.json()
        assert me_data["username"] == unique_username
        assert me_data["email"] == unique_email
        assert me_data["full_name"] is not None  # Backfilled automatically with username
        assert me_data["phone_number"] is None
        assert me_data["photo_url"] is None

        # 4. PATCH /me (Update profile fields)
        update_payload = {
            "full_name": "Budi Santoso",
            "phone_number": "+628123456789",
            "photo_url": "https://example.com/avatar.png"
        }
        resp = await client.patch("/api/v1/users/me", json=update_payload, headers=headers)
        assert resp.status_code == 200, resp.text
        updated_data = resp.json()
        assert updated_data["full_name"] == "Budi Santoso"
        assert updated_data["phone_number"] == "+628123456789"
        assert updated_data["photo_url"] == "https://example.com/avatar.png"

        # 5. GET /me (Verify changes are persistent)
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200, resp.text
        me_data = resp.json()
        assert me_data["full_name"] == "Budi Santoso"
        assert me_data["phone_number"] == "+628123456789"
        assert me_data["photo_url"] == "https://example.com/avatar.png"

        # 6. Upload avatar image via POST /users/upload-image
        file_payload = {"file": ("avatar.png", b"fake_png_data", "image/png")}
        resp = await client.post("/api/v1/users/upload-image", files=file_payload, headers=headers)
        assert resp.status_code == 200, resp.text
        upload_data = resp.json()
        assert "access_url" in upload_data
        assert upload_data["filename"] == "avatar.png"

