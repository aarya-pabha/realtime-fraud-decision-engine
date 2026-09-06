import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from src.streaming.producer import TransactionProducer, STREAM_INCOMING_QUEUE
from src.streaming.consumer import StreamingScoringConsumer, ScoringRingBuffer
from src.frontend.drift_service import DriftMonitoringService

def test_producer_load_and_publish():
    """
    Verifies that the TransactionProducer can load chronological holdout records from DuckDB
    and publish them into the streaming queue.
    """
    producer = TransactionProducer()
    records = producer.load_stream_records(limit=10)
    assert len(records) > 0, "Producer failed to load holdout records from DuckDB"
    
    first = records[0]
    assert "TransactionID" in first
    assert "TransactionAmt" in first
    assert "card1" in first
    
    # Test publishing
    success = producer.publish_transaction(first)
    assert success is True, "Failed to publish transaction into stream queue"

def test_consumer_scoring_and_ring_buffer():
    """
    Verifies that StreamingScoringConsumer executes unified C++ TreeSHAP inference,
    computes Bayesian thresholds, updates KPIs, and appends to the Ring Buffer.
    """
    test_buffer = ScoringRingBuffer(capacity=50)
    consumer = StreamingScoringConsumer(ring_buffer=test_buffer)
    
    sample_record = {
        "TransactionID": 888001,
        "TransactionDT": 15000000,
        "TransactionAmt": 1500.00,
        "ProductCD": "W",
        "card1": 13926,
        "card4": "visa",
        "card6": "credit",
        "P_emaildomain": "gmail.com",
        "R_emaildomain": "gmail.com",
        "D1": 10.0,
        "D2": 2.0
    }
    
    scored_result = consumer.score_single_event(sample_record)
    
    assert scored_result["transaction_id"] == 888001
    assert scored_result["action"] in ("APPROVE", "STEP_UP_3DS", "DECLINE")
    assert 0.0 <= scored_result["fraud_probability"] <= 1.0
    assert len(scored_result["reason_codes"]) == 3
    assert scored_result["total_latency_ms"] > 0.0
    
    # Steady-state warm run
    warm_result = consumer.score_single_event(sample_record)
    assert warm_result["total_latency_ms"] < 250.0

    
    # Assert Ring Buffer state & dynamic accumulation
    assert test_buffer.total_processed == 2
    kpis = test_buffer.get_kpis()
    assert kpis["total_processed"] == 2
    expected_total = 2 * float(sample_record["TransactionAmt"])
    assert kpis["total_amount_dollars"] == expected_total

def test_evidently_drift_monitoring_service():
    """
    Verifies that DriftMonitoringService computes Wasserstein distance and PSI
    between reference baseline distributions and streaming observations.
    """
    drift_service = DriftMonitoringService()
    drift_report = drift_service.run_drift_analysis()
    
    assert "drift_status" in drift_report
    assert "drift_share" in drift_report
    assert "drift_by_columns" in drift_report
    assert "feedback_summary" in drift_report
    
    col_drift = drift_report["drift_by_columns"]
    assert "TransactionAmt" in col_drift
    assert "prediction" in col_drift

from src.frontend.app import render_tab_content, handle_ramp_presets, update_ramp_simulator, update_kpi_metrics, update_ops_forensics, handle_ops_feedback, update_drift_center

def test_dash_app_ramp_editorial_workstation_rendering():
    """
    Verifies that Ramp Editorial Calm tabs render seamlessly across all functional modules.
    """
    # 1. Test Tab Rendering
    sim_view, _, _, _ = render_tab_content("tab-sim")
    ops_view, _, _, _ = render_tab_content("tab-ops")
    drift_view, _, _, _ = render_tab_content("tab-drift")
    
    assert sim_view is not None
    assert ops_view is not None
    assert drift_view is not None
    
    # 2. Test 1-Click Scenario Presets
    a_amt, a_vel, a_prod, a_em = handle_ramp_presets(None, None, 1)
    assert a_amt == 45
    assert a_vel == 8
    assert a_em == "disposable"
    
    # 3. Test Interactive Simulator Callback
    amt_s, vel_s, act, sty, expl, fig, thresh, reasons, lat = update_ramp_simulator(
        amount=25, velocity=1, product_cd="W", email_mode="match"
    )
    assert fig is not None
    assert "DIRECT APPROVAL" in act
    assert "$25.00" in amt_s
    
    # 4. Test Live Operations Forensics & Dispute Feedback
    mock_table = [{"transaction_id": "3485215", "transaction_amount": "$100.00", "fraud_probability": "0.05", "action": "APPROVE", "primary_reason": "STANDARD"}]
    forensics = update_ops_forensics([0], mock_table)
    assert forensics is not None
    
    # 5. Test Evidently AI Drift Center Callback
    drift_fig, drift_status, fb_text = update_drift_center(1)
    assert drift_fig is not None
    assert "STABLE" in drift_status or "DRIFT" in drift_status
    assert "Labels Logged" in fb_text






