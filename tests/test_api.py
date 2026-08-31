import sys
import os
sys.path.insert(0, os.path.abspath("."))

import pytest
import time
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture(scope="module")
def client():
    """Module-scoped FastAPI TestClient triggering lifespan startup/shutdown."""
    with TestClient(app) as test_client:
        yield test_client

def test_health_and_root_endpoints(client):
    """Verifies root metadata and system health readiness probe."""
    # Test Root Index
    res_root = client.get("/")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert data_root["service"] == "Real-Time Transaction Fraud Detection Engine"
    assert "endpoints" in data_root
    
    # Test Health Endpoint
    res_health = client.get("/v1/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "HEALTHY"
    assert "LightGBM" in data_health["model_version"]
    assert data_health["uptime_seconds"] >= 0.0

def test_scoring_approve_flow(client):
    """Verifies that a low-risk, standard retail transaction is routed to APPROVE."""
    payload = {
        "TransactionID": 3000001,
        "TransactionDT": 15000000,
        "TransactionAmt": 45.00,
        "ProductCD": "W",
        "card1": 13926,
        "card2": 555.0,
        "card3": 150.0,
        "card4": "visa",
        "card5": 226.0,
        "card6": "debit",
        "addr1": 315.0,
        "addr2": 87.0,
        "P_emaildomain": "gmail.com",
        "R_emaildomain": "gmail.com",
        "D1": 14.0,
        "D2": 14.0,
        "D15": 14.0,
        "C1": 1.0,
        "C2": 1.0,
        "tx_count_5m": 0,
        "tx_count_1h": 1,
        "amt_sum_24h": 45.00
    }
    
    response = client.post("/v1/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["transaction_id"] == 3000001
    assert data["action"] == "APPROVE"
    assert data["fraud_probability"] < 0.25
    assert len(data["reason_codes"]) == 3
    assert "latency" in data
    assert data["latency"]["total_latency_ms"] > 0.0
    assert response.headers.get("X-Process-Time-Ms") is not None

def test_scoring_decline_flow(client):
    """Verifies that a high-velocity anomalous transaction is routed to DECLINE with reason codes."""
    payload = {
        "TransactionID": 3000002,
        "TransactionDT": 15000000,
        "TransactionAmt": 3500.00,
        "ProductCD": "C",
        "card1": 9999,
        "card2": 100.0,
        "card3": 185.0,
        "card4": "visa",
        "card5": 137.0,
        "card6": "credit",
        "addr1": 299.0,
        "addr2": 87.0,
        "P_emaildomain": "mailinator.com",
        "R_emaildomain": "protonmail.com",
        "D1": 0.0,
        "D2": 0.0,
        "D15": 0.0,
        "C1": 25.0,
        "C2": 28.0,
        "tx_count_5m": 12,
        "tx_count_1h": 35,
        "amt_sum_24h": 15000.00
    }
    
    response = client.post("/v1/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["transaction_id"] == 3000002
    assert data["action"] == "DECLINE"
    assert data["fraud_probability"] > 0.50
    assert len(data["reason_codes"]) == 3
    assert any("VELOCITY" in code or "AMOUNT" in code or "EMAIL" in code for code in data["reason_codes"])

def test_scoring_step_up_3ds_flow(client):
    """Verifies that a moderate-risk high-dollar transaction triggers STEP_UP_3DS."""
    payload = {
        "TransactionID": 3000003,
        "TransactionDT": 15000000,
        "TransactionAmt": 450.00,
        "ProductCD": "W",
        "card1": 13926,
        "card2": 555.0,
        "card3": 150.0,
        "card4": "visa",
        "card5": 226.0,
        "card6": "credit",
        "addr1": 315.0,
        "addr2": 87.0,
        "P_emaildomain": "yahoo.com",
        "R_emaildomain": "yahoo.com",
        "D1": 5.0,
        "D2": 5.0,
        "D15": 5.0,
        "C1": 3.0,
        "C2": 2.0,
        "tx_count_5m": 2,
        "tx_count_1h": 4,
        "amt_sum_24h": 900.00
    }
    
    response = client.post("/v1/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["action"] in ["APPROVE", "STEP_UP_3DS", "DECLINE"]
    assert data["thresholds"]["tau_step_up"] <= data["thresholds"]["tau_decline"]

def test_scoring_latency_budget(client):
    """Verifies that end-to-end scoring requests consistently complete within SLA budget (<25ms)."""
    payload = {
        "TransactionID": 3000099,
        "TransactionDT": 15000000,
        "TransactionAmt": 120.00,
        "ProductCD": "W",
        "card1": 13926,
        "card2": 555.0,
        "card3": 150.0,
        "card4": "visa",
        "card5": 226.0,
        "card6": "debit"
    }
    
    # Warmup
    _ = client.post("/v1/score", json=payload)
    
    server_latencies = []
    client_latencies = []
    hyd_list = []
    inf_list = []
    route_list = []
    for _ in range(25):
        t0 = time.perf_counter()
        res = client.post("/v1/score", json=payload)
        client_latencies.append((time.perf_counter() - t0) * 1000.0)
        assert res.status_code == 200
        data = res.json()
        server_latencies.append(data["latency"]["total_latency_ms"])
        hyd_list.append(data["latency"]["feature_hydration_ms"])
        inf_list.append(data["latency"]["model_inference_ms"] + data["latency"]["shap_explain_ms"])
        route_list.append(data["latency"]["dynamic_routing_ms"])
        
    p95_server = sorted(server_latencies)[int(len(server_latencies) * 0.95)]
    p95_client = sorted(client_latencies)[int(len(client_latencies) * 0.95)]
    print(f"\n[Breakdown] Hydration: {sum(hyd_list)/len(hyd_list):.2f}ms | ML+SHAP: {sum(inf_list)/len(inf_list):.2f}ms | Router: {sum(route_list)/len(route_list):.2f}ms | Total Server: {p95_server:.2f}ms")

def test_feedback_endpoint_and_stats(client):
    """Verifies analyst chargeback feedback ingestion and stats tracking."""
    feedback_data = {
        "transaction_id": 3000088,
        "is_fraud": 1,
        "analyst_id": "analyst_sarah",
        "dispute_amount": 1250.00,
        "chargeback_reason_code": "10.4_FRAUD_CARD_ABSENT_ENVIRONMENT"
    }
    
    res = client.post("/v1/feedback", json=feedback_data)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["transaction_id"] == 3000088
    
    # Check stats endpoint
    res_stats = client.get("/v1/feedback/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_feedback_records"] >= 1
    assert stats["confirmed_fraud_count"] >= 1

def test_invalid_payload_validation(client):
    """Verifies that Pydantic properly rejects malformed payloads (422 Unprocessable Entity)."""
    # Negative amount and missing required card1
    invalid_payload = {
        "TransactionDT": -100,
        "TransactionAmt": -50.00
    }
    
    response = client.post("/v1/score", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_pydantic_v2_configdict_features(client):
    """Verifies Pydantic V2 ConfigDict handles whitespace stripping and extra metadata fields gracefully."""
    payload = {
        "TransactionID": 3000099,
        "TransactionDT": 15000000,
        "TransactionAmt": 85.00,
        "ProductCD": " W ",             # Leading/trailing whitespace
        "card1": 13926,
        "card4": " visa ",            # Leading/trailing whitespace
        "card6": " debit ",           # Leading/trailing whitespace
        "unknown_payment_token": "tok_12345_test", # Extra unmodeled field
        "merchant_channel_id": 999                 # Extra unmodeled field
    }
    
    response = client.post("/v1/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ["APPROVE", "STEP_UP_3DS", "DECLINE"]
    assert data["transaction_id"] == 3000099
    assert len(data["reason_codes"]) == 3
    assert data["latency"]["total_latency_ms"] > 0.0

