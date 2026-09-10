import pytest
import os
import sys
sys.path.insert(0, os.path.abspath("."))

import pandas as pd
import lightgbm as lgb
import sqlite3
from src.models.explainability import FraudExplainer
from src.models.dataset_loader import get_temporal_splits

def test_model_artifact_exists():
    assert os.path.exists("models/fraud_lgb_model.txt"), "Trained model artifact missing!"

def test_model_prediction_range():
    model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    _, _, _, _, X_test, y_test, _, _ = get_temporal_splits()
    sample = X_test.head(100)
    preds = model.predict(sample)
    
    assert (preds >= 0.0).all() and (preds <= 1.0).all(), "Predictions outside [0, 1]!"
    assert len(preds) == 100

def test_shap_reason_codes_latency_and_format():
    explainer = FraudExplainer("models/fraud_lgb_model.txt")
    _, _, _, _, X_test, _, _, _ = get_temporal_splits()
    sample = X_test.head(1)
    
    # Warm-up call for JIT / cache setup
    _ = explainer.explain_transaction(sample)
    
    # Steady-state SLA evaluation
    res = explainer.explain_transaction(sample)
    assert len(res['reason_codes']) == 3, "Did not return exactly 3 reason codes"
    assert res['latency_ms'] < 25.0, f"SHAP latency exceeds SLA: {res['latency_ms']:.2f}ms"
    for code in res['reason_codes']:
        assert isinstance(code, str) and len(code) > 0

def test_conditional_predict_proba_and_explain():
    from src.models.explainability import DEFAULT_APPROVE_REASON_CODES
    explainer = FraudExplainer("models/fraud_lgb_model.txt")
    _, _, _, _, X_test, _, _, _ = get_temporal_splits()
    sample = X_test.head(1)
    
    # Warm-up call for internal C++ buffer and threadpool allocation
    _ = explainer.predict_proba(sample)
    _ = explainer.explain(sample)
    
    # 1. Test predict_proba ultra-fast inference (<10ms SLA)
    prob_fast, lat_fast = explainer.predict_proba(sample)
    assert 0.0 <= prob_fast <= 1.0, f"Invalid probability: {prob_fast}"
    assert lat_fast < 15.0, f"Pure predict latency too high: {lat_fast:.2f}ms"
    
    # 2. Test explain TreeSHAP attribution
    reasons, lat_shap = explainer.explain(sample)
    assert len(reasons) == 3, f"Expected 3 reason codes, got {len(reasons)}"
    assert lat_shap < 25.0, f"TreeSHAP latency exceeded SLA: {lat_shap:.2f}ms"
    
    # 3. Test numerical equivalence with score_and_explain
    prob_unified, reasons_unified, _ = explainer.score_and_explain(sample)
    assert abs(prob_fast - prob_unified) < 1e-5, f"Probability mismatch: {prob_fast} vs {prob_unified}"
    assert reasons == reasons_unified, f"Reason codes mismatch: {reasons} vs {reasons_unified}"
    
    # 4. Verify default approve codes contract
    assert len(DEFAULT_APPROVE_REASON_CODES) == 3
    for code in DEFAULT_APPROVE_REASON_CODES:
        assert isinstance(code, str) and len(code) > 0


def test_mlflow_sqlite_run_logged():
    assert os.path.exists("mlruns.db"), "mlruns.db SQLite database does not exist!"
    con = sqlite3.connect("mlruns.db")
    runs = pd.read_sql("SELECT * FROM runs WHERE status = 'FINISHED'", con)
    metrics = pd.read_sql("SELECT DISTINCT key FROM metrics", con)
    con.close()
    
    assert len(runs) > 0, "No finished MLflow runs found!"
    assert 'test_roc_auc' in metrics['key'].values, "test_roc_auc metric not logged!"
    assert 'test_pr_auc' in metrics['key'].values, "test_pr_auc metric not logged!"
