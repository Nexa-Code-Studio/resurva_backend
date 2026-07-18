import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.enums import WalletType, WalletTransactionType, WalletTransactionCategory, TransactionStatus


@pytest.mark.anyio
async def test_wallet_and_withdrawals_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]
        
        # 1. Setup Business
        business_payload = {
            "name": f"Wallet Test Biz {unique_suffix}",
            "email": f"biz_{unique_suffix}@test.com",
            "phone": "0812345678"
        }
        resp = await ac.post("/api/v1/businesses/", json=business_payload)
        assert resp.status_code == 201
        business_id = resp.json()["id"]

        # 2. Setup User (Owner)
        owner_payload = {
            "username": f"owner_{unique_suffix}",
            "email": f"owner_{unique_suffix}@test.com",
            "password": "password123",
            "role": "owner",
            "business_id": business_id
        }
        resp = await ac.post("/api/v1/auth/register", json=owner_payload)
        assert resp.status_code == 201

        # 3. Login
        login_payload = {
            "username_or_email": f"owner_{unique_suffix}",
            "password": "password123"
        }
        resp = await ac.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 4. Create Store (triggers both wallets creation)
        store_payload = {
            "name": f"Wallet Store {unique_suffix}",
            "address": "Jalan Wallet 12",
            "city": "Malang",
            "latitude": -7.98,
            "longitude": 112.62,
            "business_id": business_id,
            "is_active": True
        }
        resp = await ac.post("/api/v1/stores/", json=store_payload, headers=headers)
        assert resp.status_code == 201
        store_id = resp.json()["id"]

        # 5. Verify Store Wallets balances
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances", headers=headers)
        assert resp.status_code == 200
        balances = resp.json()
        assert balances["digital"] == 0
        assert balances["offline"] == 0

        # 6. Verify individual wallet retrieval
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}?type=digital", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["type"] == "digital"

        resp = await ac.get(f"/api/v1/wallets/store/{store_id}?type=offline", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["type"] == "offline"

        # 7. Create Manual Transaction (Income to Offline Wallet)
        tx_income_payload = {
            "wallet_type": "offline",
            "type": "credit",
            "category": "catCapital",
            "amount": 5000000,
            "note": "Modal Awal Toko"
        }
        resp = await ac.post(f"/api/v1/wallets/store/{store_id}/transactions", json=tx_income_payload, headers=headers)
        assert resp.status_code == 200
        tx_income = resp.json()
        assert tx_income["amount"] == 5000000
        assert tx_income["type"] == "credit"
        assert tx_income["category"] == "catCapital"

        # Verify offline balance is now 5,000,000
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances", headers=headers)
        assert resp.json()["offline"] == 5000000

        # 8. Create Manual Transaction (Expense from Offline Wallet)
        tx_expense_payload = {
            "wallet_type": "offline",
            "type": "debit",
            "category": "catRent",
            "amount": 1000000,
            "note": "Bayar Sewa Bulanan"
        }
        resp = await ac.post(f"/api/v1/wallets/store/{store_id}/transactions", json=tx_expense_payload, headers=headers)
        assert resp.status_code == 200
        tx_expense = resp.json()
        assert tx_expense["amount"] == 1000000
        assert tx_expense["type"] == "debit"

        # Verify offline balance is now 4,000,000
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances", headers=headers)
        assert resp.json()["offline"] == 4000000

        # 9. Verify unified transactions list
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/transactions", headers=headers)
        assert resp.status_code == 200
        txs = resp.json()
        assert len(txs) == 2
        assert txs[0]["id"] == tx_expense["id"]
        assert txs[1]["id"] == tx_income["id"]

        # 10. Delete Expense Transaction (reverses balance)
        resp = await ac.delete(f"/api/v1/wallets/transactions/{tx_expense['id']}", headers=headers)
        assert resp.status_code == 204

        # Verify offline balance is back to 5,000,000
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances", headers=headers)
        assert resp.json()["offline"] == 5000000

        # 11. Test Withdrawals (from Digital Wallet)
        # First, add credit to digital wallet so we can withdraw
        tx_digital_credit = {
            "wallet_type": "digital",
            "type": "credit",
            "category": "catAdjustment",
            "amount": 2000000,
            "note": "Topup digital wallet"
        }
        resp = await ac.post(f"/api/v1/wallets/store/{store_id}/transactions", json=tx_digital_credit, headers=headers)
        assert resp.status_code == 200

        # Submit withdrawal
        withdraw_payload = {
            "bank_name": "BCA",
            "account_number": "8412852230",
            "account_holder": "AHMAD HIDAYAT",
            "amount": 1500000,
            "save_account": True
        }
        resp = await ac.post(f"/api/v1/wallets/store/{store_id}/withdrawals", json=withdraw_payload, headers=headers)
        assert resp.status_code == 200
        withdrawal = resp.json()
        assert withdrawal["amount"] == 1500000
        assert withdrawal["status"] == "pending"
        assert withdrawal["bank_name"] == "BCA"

        # Verify digital wallet balance deducted (2,000,000 - 1,500,000 = 500,000)
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances", headers=headers)
        assert resp.json()["digital"] == 500000

        # Verify saved bank info on digital wallet
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}?type=digital", headers=headers)
        saved_info = resp.json()["saved_bank_info"]
        assert saved_info["bankName"] == "BCA"
        assert saved_info["accountNumber"] == "8412852230"

        # Verify withdrawal list
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/withdrawals", headers=headers)
        assert len(resp.json()) == 1

        # Cancel withdrawal
        resp = await ac.post(f"/api/v1/wallets/withdrawals/{withdrawal['id']}/cancel", headers=headers)
        assert resp.status_code == 200
        cancelled = resp.json()
        assert cancelled["status"] == "failed"

        # Verify digital wallet balance refunded (back to 2,000,000)
        resp = await ac.get(f"/api/v1/wallets/store/{store_id}/balances", headers=headers)
        assert resp.json()["digital"] == 2000000
