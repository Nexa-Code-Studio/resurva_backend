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
