import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_stream_recent_and_kpis(client):
    res_recent = client.get("/v1/stream/recent?limit=5")
    assert res_recent.status_code == 200
    items = res_recent.json()
    assert isinstance(items, list)
    assert len(items) > 0
    assert "transaction_id" in items[0]
    assert "fraud_probability" in items[0]
    assert "action" in items[0]

    res_kpis = client.get("/v1/stream/kpis")
    assert res_kpis.status_code == 200
    kpis = res_kpis.json()
    assert "total_processed" in kpis
    assert "approval_rate_pct" in kpis
    assert "p95_latency_ms" in kpis

def test_stream_simulate(client):
    payload = {
        "TransactionAmt": 2400.0,
        "ProductCD": "H",
        "card1": 4242,
        "card2": 500,
        "card3": 150,
        "card4": "visa",
        "card6": "credit",
        "P_emaildomain": "anonymous.com",
        "C1": 5.0,
        "C2": 5.0
    }
    res = client.post("/v1/stream/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["transaction_amount"] == 2400.0
    assert "action" in data
    assert "fraud_probability" in data
    assert "reason_codes" in data

def test_stream_replay(client):
    res = client.post("/v1/stream/replay")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "replayed"
    assert "total_seeded" in data

    # Verify buffer contains fresh items starting from index 0
    res_recent = client.get("/v1/stream/recent?limit=5")
    assert res_recent.status_code == 200
    items = res_recent.json()
    assert len(items) > 0
