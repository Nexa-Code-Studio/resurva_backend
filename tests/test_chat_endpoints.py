import uuid
import pytest
from httpx import ASGITransport, AsyncClient

# Import all models via test_chatbot_security to register them
from tests.test_chatbot_security import Base, User, Store, Business
from app.main import app

@pytest.mark.anyio
async def test_chat_messages_sorted_flow():
    """
    Verify that:
    1. POST /chat/conversations/{conversation_id}/messages returns the full list of messages.
    2. Messages returned by both POST and GET endpoints are sorted ascending by created_at.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]
        username = f"seller_{unique_suffix}"
        email = f"seller_{unique_suffix}@resurvafoods.com"
        business_email = f"business_{unique_suffix}@resurvafoods.com"

        # 1. Create Business
        business_payload = {
            "name": "Resurva Test Foods Co",
            "email": business_email,
            "phone": "0812345678"
        }
        resp = await ac.post("/api/v1/businesses/", json=business_payload)
        assert resp.status_code == 201, resp.text
        business_id = resp.json()["id"]

        # 2. Create Store
        store_payload = {
            "name": "Resurva Test Store",
            "address": "Green Boulevard",
            "city": "Bandung",
            "longitude": 107.61,
            "latitude": -6.91,
            "business_id": business_id,
            "is_active": True
        }
        resp = await ac.post("/api/v1/stores/", json=store_payload)
        assert resp.status_code == 201, resp.text
        store_id = resp.json()["id"]

        # 3. Register User as Seller
        owner_payload = {
            "username": username,
            "email": email,
            "password": "securepassword123",
            "role": "seller",
            "business_id": business_id,
            "store_id": store_id
        }
        resp = await ac.post("/api/v1/auth/register", json=owner_payload)
        assert resp.status_code == 201, resp.text

        # 4. Login (Get JWT Token)
        login_payload = {
            "username_or_email": username,
            "password": "securepassword123"
        }
        resp = await ac.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 5. Create Conversation
        conv_payload = {
            "store_id": store_id,
            "title": "Sorting Test Chat"
        }
        resp = await ac.post("/api/v1/chat/conversations", headers=headers, json=conv_payload)
        assert resp.status_code == 201, resp.text
        conv_id = resp.json()["id"]

        # 6. Send message (POST messages endpoint)
        print("Sending message...")
        resp = await ac.post(f"/api/v1/chat/conversations/{conv_id}/messages?user_message=halo", headers=headers)
        assert resp.status_code == 200, resp.text
        
        # Verify response model is list of messages
        messages = resp.json()
        assert isinstance(messages, list)
        assert len(messages) >= 2  # Should contain at least the user message and assistant message
        
        # Verify that messages are sorted by created_at (ascending order)
        prev_time = ""
        for m in messages:
            # Check fields
            assert "role" in m
            assert "content" in m
            assert "created_at" in m
            
            curr_time = m["created_at"]
            if prev_time:
                assert curr_time >= prev_time
            prev_time = curr_time

        # 7. Get messages (GET messages endpoint)
        print("Getting messages...")
        resp = await ac.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers)
        assert resp.status_code == 200, resp.text
        
        get_messages = resp.json()
        assert isinstance(get_messages, list)
        assert len(get_messages) == len(messages)
        
        # Verify that GET messages are also sorted by created_at
        prev_time = ""
        for m in get_messages:
            curr_time = m["created_at"]
            if prev_time:
                assert curr_time >= prev_time
            prev_time = curr_time

        from app.db.session import engine
        await engine.dispose()


@pytest.mark.anyio
async def test_chat_skills_flow():
    """
    Verify that:
    1. A conversation can be created with or without a skill.
    2. Modifying a conversation's skill via PATCH works and persists.
    3. A system notification message is added when the skill changes.
    4. Invalid skills are rejected.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]
        username = f"seller_{unique_suffix}"
        email = f"seller_{unique_suffix}@resurvafoods.com"
        business_email = f"business_{unique_suffix}@resurvafoods.com"

        # 1. Create Business
        business_payload = {
            "name": "Resurva Test Foods Co",
            "email": business_email,
            "phone": "0812345678"
        }
        resp = await ac.post("/api/v1/businesses/", json=business_payload)
        assert resp.status_code == 201
        business_id = resp.json()["id"]

        # 2. Create Store
        store_payload = {
            "name": "Resurva Test Store",
            "address": "Green Boulevard",
            "city": "Bandung",
            "longitude": 107.61,
            "latitude": -6.91,
            "business_id": business_id,
            "is_active": True
        }
        resp = await ac.post("/api/v1/stores/", json=store_payload)
        assert resp.status_code == 201
        store_id = resp.json()["id"]

        # 3. Register User as Seller
        owner_payload = {
            "username": username,
            "email": email,
            "password": "securepassword123",
            "role": "seller",
            "business_id": business_id,
            "store_id": store_id
        }
        resp = await ac.post("/api/v1/auth/register", json=owner_payload)
        assert resp.status_code == 201

        # 4. Login
        login_payload = {
            "username_or_email": username,
            "password": "securepassword123"
        }
        resp = await ac.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 5. Create Conversation (default None skill)
        conv_payload = {
            "store_id": store_id,
            "title": "Skills Test Chat",
            "active_skill": None
        }
        resp = await ac.post("/api/v1/chat/conversations", headers=headers, json=conv_payload)
        assert resp.status_code == 201
        conv_data = resp.json()
        assert conv_data["active_skill"] is None
        conv_id = conv_data["id"]

        # 6. PATCH to update skill to 'strategi'
        resp = await ac.patch(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=headers, 
            json={"active_skill": "strategi"}
        )
        assert resp.status_code == 200
        assert resp.json()["active_skill"] == "strategi"

        # 7. Verify a system message is appended
        resp = await ac.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers)
        assert resp.status_code == 200
        messages = resp.json()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "Strategi 🧠" in messages[0]["content"]

        # 8. PATCH to update skill to 'umum'
        resp = await ac.patch(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=headers, 
            json={"active_skill": "umum"}
        )
        assert resp.status_code == 200
        assert resp.json()["active_skill"] is None

        # 9. Verify invalid skill rejection
        resp = await ac.patch(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=headers, 
            json={"active_skill": "invalid_skill_name"}
        )
        assert resp.status_code == 400

        from app.db.session import engine
        await engine.dispose()

