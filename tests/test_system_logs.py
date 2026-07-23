import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_logs_creation_and_retrieval():
    """Verify LogSystem POST, GET, middleware auto-logs, and explicit auth logs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test POST /api/v1/logs/ (anonymous client logging)
        payload = {
            "platform": "mobile_client",
            "severity": "INFO",
            "event": "Test client log event",
            "user_email": "test-client@email.com",
            "ip_address": "127.0.0.1",
            "details": {"client": "FlutterApp"}
        }
        resp = await ac.post("/api/v1/logs/", json=payload)
        assert resp.status_code == 201, resp.text
        log_data = resp.json()
        assert log_data["event"] == "Test client log event"
        assert log_data["platform"] == "mobile_client"
        assert log_data["user_email"] == "test-client@email.com"

        # 2. Register an admin to query logs
        unique_suffix = uuid.uuid4().hex[:8]
        admin_username = f"admin_{unique_suffix}"
        admin_email = f"admin_{unique_suffix}@resurva.com"
        
        register_payload = {
            "username": admin_username,
            "email": admin_email,
            "password": "adminpassword123",
            "role": "admin"
        }
        resp = await ac.post("/api/v1/auth/register", json=register_payload)
        assert resp.status_code == 201, resp.text
        
        # 3. Login as Admin
        login_payload = {
            "username_or_email": admin_username,
            "password": "adminpassword123"
        }
        resp = await ac.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 4. Query GET /api/v1/logs/ (with admin auth)
        resp = await ac.get("/api/v1/logs/", headers=headers)
        assert resp.status_code == 200, resp.text
        logs_data = resp.json()
        assert "items" in logs_data
        assert logs_data["pagination"]["total"] >= 1
        
        # 5. Verify middleware automatic logging
        # Make a POST request to create a business
        biz_payload = {
            "name": f"Business for Logging_{unique_suffix}",
            "email": f"biz_{unique_suffix}@email.com",
            "phone": "0812345"
        }
        resp = await ac.post("/api/v1/businesses/", json=biz_payload, headers=headers)
        assert resp.status_code == 201, resp.text
        
        # Query GET /api/v1/logs/ with search to check if middleware automatically logged the POST
        resp = await ac.get("/api/v1/logs/?search=businesses", headers=headers)
        assert resp.status_code == 200, resp.text
        search_results = resp.json()["items"]
        assert len(search_results) >= 1
        assert "businesses" in search_results[0]["event"]
