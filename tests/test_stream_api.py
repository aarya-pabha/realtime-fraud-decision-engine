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
    # Seed a feedback dispute first
    client.post("/v1/feedback", json={
        "transaction_id": 999999,
        "is_fraud": 1,
        "analyst_id": "test_analyst"
    })
    
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

    # Verify feedback store was cleared by replay
    res_drift = client.get("/v1/stream/drift")
    assert res_drift.status_code == 200
    assert res_drift.json()["feedback_summary"]["total_disputes"] == 0

def test_stream_drift_endpoint(client):
    res = client.get("/v1/stream/drift")
    assert res.status_code == 200
    data = res.json()
    assert "drift_status" in data
    assert "drift_by_columns" in data
    assert "feedback_summary" in data
    assert "TransactionAmt" in data["drift_by_columns"]
    assert "total_disputes" in data["feedback_summary"]

    # Test trigger on-demand run
    res_run = client.post("/v1/stream/drift/run")
    assert res_run.status_code == 200
    data_run = res_run.json()
    assert "drift_status" in data_run

def test_stream_drift_inject_and_reset(client):
    # Inject drift wave
    res_inject = client.post("/v1/stream/drift/inject")
    assert res_inject.status_code == 200
    data_inject = res_inject.json()
    assert data_inject["drift_status"] == "DRIFT_DETECTED"
    assert data_inject["dataset_drift"] is True
    assert data_inject["number_of_drifted_columns"] >= 2
    assert data_inject["drift_by_columns"]["TransactionAmt"]["drift_score"] >= 0.10
    assert data_inject["drift_by_columns"]["tx_count_5m"]["drift_score"] >= 0.10

    # Reset drift back to baseline
    res_reset = client.post("/v1/stream/drift/reset")
    assert res_reset.status_code == 200
    data_reset = res_reset.json()
    assert data_reset["drift_status"] == "STABLE"
    assert data_reset["dataset_drift"] is False
    assert data_reset["number_of_drifted_columns"] == 0
    assert data_reset["drift_by_columns"]["TransactionAmt"]["drift_score"] < 0.10


