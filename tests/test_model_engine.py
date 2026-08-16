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


def test_mlflow_sqlite_run_logged():
    assert os.path.exists("mlruns.db"), "mlruns.db SQLite database does not exist!"
    con = sqlite3.connect("mlruns.db")
    runs = pd.read_sql("SELECT * FROM runs WHERE status = 'FINISHED'", con)
    metrics = pd.read_sql("SELECT DISTINCT key FROM metrics", con)
    con.close()
    
    assert len(runs) > 0, "No finished MLflow runs found!"
    assert 'test_roc_auc' in metrics['key'].values, "test_roc_auc metric not logged!"
    assert 'test_pr_auc' in metrics['key'].values, "test_pr_auc metric not logged!"
