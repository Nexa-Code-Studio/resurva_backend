import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_enterprise_finance_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unique_suffix = uuid.uuid4().hex[:8]

        # 1. Create Business
        business_payload = {
            "name": f"Enterprise Test {unique_suffix}",
            "email": f"corp_{unique_suffix}@enterprise.com",
            "phone": "0812999888"
        }
        resp = await ac.post("/api/v1/businesses/", json=business_payload)
        assert resp.status_code == 201
        business_id = resp.json()["id"]

        # 2. Get/Create HQ Wallet
        resp = await ac.get(f"/api/v1/wallets/business/{business_id}/hq")
        assert resp.status_code == 200
        wallet_data = resp.json()
        assert wallet_data["business_id"] == business_id
        assert wallet_data["type"] == "hq"
        assert wallet_data["balance"] == 0

        # 3. Create HQ Credit Transaction (Setoran Cabang)
        credit_payload = {
            "wallet_type": "hq",
            "type": "credit",
            "category": "catBranchDeposit",
            "amount": 50000000,
            "note": "Setoran Cabang Malang",
            "transaction_date": "2026-07-20T10:00:00Z"
        }
        resp = await ac.post(f"/api/v1/wallets/business/{business_id}/transactions", json=credit_payload)
        assert resp.status_code == 200
        tx_data = resp.json()
        assert tx_data["amount"] == 50000000
        assert tx_data["balance_after"] == 50000000

        # 4. Create HQ Debit Transaction (Gaji Staf HQ)
        debit_payload = {
            "wallet_type": "hq",
            "type": "debit",
            "category": "catSalary",
            "amount": 15000000,
            "note": "Gaji HQ",
            "transaction_date": "2026-07-20T11:00:00Z"
        }
        resp = await ac.post(f"/api/v1/wallets/business/{business_id}/transactions", json=debit_payload)
        assert resp.status_code == 200
        assert resp.json()["balance_after"] == 35000000

        # 5. List HQ Transactions
        resp = await ac.get(f"/api/v1/wallets/business/{business_id}/transactions")
        assert resp.status_code == 200
        txs = resp.json()
        assert len(txs) == 2

        # 6. Fetch Enterprise Finance Analytics
        resp = await ac.get(f"/api/v1/analytics/enterprise/finance?business_id={business_id}")
        assert resp.status_code == 200
        analytics = resp.json()
        assert "gmv" in analytics
        assert "total_combined_profit" in analytics
        assert analytics["hq_operational_expense"] == 15000000
        assert len(analytics["cashflow_monthly"]) == 6
