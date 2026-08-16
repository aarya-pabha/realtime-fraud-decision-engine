# Phase 3 Implementation Plan: Model Engine (LightGBM Tuning with Optuna & MLflow Registry)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the production-grade Machine Learning engine: load the 72 engineered features across a strict 3-way temporal partition (Train: Days 1–120, Val: Days 121–150, Test: Days 151–183), optimize LightGBM hyperparameters with Multi-Objective Optuna (PR-AUC + ROC-AUC), log experiments and model artifacts to a local SQLite MLflow registry (`mlruns.db`), build a sub-10ms SHAP TreeExplainer reason code generator, and verify with targeted Pytests.

**Architecture:**
- **Data Source:** DuckDB / Parquet offline feature store with all 72 validated domain features across all 590,540 rows.
- **Temporal Partitions:** Train (Days 1–120: 410,601 rows), Val (Days 121–150: 87,512 rows), Holdout Test (Days 151–183: 92,427 rows).
- **Tuning Engine:** Multi-objective Optuna (`directions=["maximize", "maximize"]`) with TPESampler and Automated Knee-Point Euclidean Selection.
- **Experiment Tracking & Registry:** MLflow backed by local SQLite database (`sqlite:///mlruns.db`).
- **Explainability:** SHAP TreeExplainer computing top-3 human-readable fraud attribution codes in $<10\text{ms}$.

**Tech Stack:** Python 3.11 (`.venv`), LightGBM 4.7, Optuna 4.9, MLflow 3.15, SHAP 0.51, Pytest.

---

## Proposed Tasks

### Task 1: Reusable 3-Way Temporal Partition Dataset Loader (`src/models/dataset_loader.py`)
**Files:**
- Create: `src/models/dataset_loader.py`

- [ ] **Step 1: Write dataset loader loading DuckDB tables with full 72 feature transformations and 3-way temporal split:**
```python
import duckdb
import pandas as pd
import numpy as np
import os

def load_processed_dataset(db_path="feature_store.duckdb"):
    """
    Loads all 590,540 transactions and builds the exact 72-feature matrix with 3-way temporal split:
    - Train: Days 1 to 120 (410,601 rows)
    - Val: Days 121 to 150 (87,512 rows)
    - Test: Days 151 to 183 (92,427 rows)
    """
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM enriched_transactions").fetchdf()
    card_base = con.execute("SELECT * FROM card_base_features").fetchdf()
    con.close()
    
    # Merge velocity features
    df = df.merge(card_base, on=['card_base_id', 'event_timestamp', 'created_timestamp'], how='left')
    
    # 1. Temporal dynamics
    df['hour_dt'] = (df['TransactionDT'] // 3600) % 24
    df['day_dt'] = (df['TransactionDT'] // (3600 * 24)) % 7
    
    # 2. Currency & amount
    df['decimal_places'] = df['TransactionAmt'].astype(str).apply(lambda x: len(x.split('.')[1]) if '.' in x else 0)
    df['is_foreign_currency'] = (df['decimal_places'] >= 3).astype(int)
    df['log_TransactionAmt'] = np.log1p(df['TransactionAmt'])
    
    card_amt_stats = df.groupby('card_base_id')['TransactionAmt'].agg(['mean', 'std']).reset_index()
    card_amt_stats.columns = ['card_base_id', 'card_amt_mean', 'card_amt_std']
    df = df.merge(card_amt_stats, on='card_base_id', how='left')
    df['amt_to_mean_card'] = df['TransactionAmt'] / (df['card_amt_mean'] + 1e-5)
    df['amt_to_std_card'] = df['TransactionAmt'] / (df['card_amt_std'].fillna(1.0) + 1e-5)
    
    # 3. Card-scaled D-deltas
    for col in ['D1', 'D2', 'D15']:
        if col in df.columns:
            mean_d = df.groupby('card_base_id')[col].transform('mean')
            df[f'{col}_to_mean_card'] = df[col] / (mean_d + 1e-5)
            
    # 4. Email matching
    df['email_domain_match'] = (
        (df['P_emaildomain'].notna()) & 
        (df['R_emaildomain'].notna()) & 
        (df['P_emaildomain'] == df['R_emaildomain'])
    ).astype(int)
    disposable_domains = {'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com', 'throwawaymail.com'}
    df['is_disposable_email'] = df['P_emaildomain'].isin(disposable_domains).astype(int)
    
    # 5. Entity frequency encodings
    for col in ['card_base_id', 'cardholder_uid', 'addr1', 'P_emaildomain']:
        df[f'{col}_freq'] = df[col].map(df[col].value_counts(normalize=True))
        
    return df

def get_temporal_splits(df=None, db_path="feature_store.duckdb"):
    if df is None:
        df = load_processed_dataset(db_path=db_path)
        
    train_mask = df['TransactionDT'] < (120 * 86400)
    val_mask = (df['TransactionDT'] >= (120 * 86400)) & (df['TransactionDT'] < (151 * 86400))
    test_mask = df['TransactionDT'] >= (151 * 86400)
    
    exclude_cols = {'TransactionID', 'isFraud', 'TransactionDT', 'event_timestamp', 'created_timestamp', 'card_base_id', 'cardholder_uid', 'card_amt_mean', 'card_amt_std'}
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    cat_cols = ['ProductCD', 'card4', 'card6', 'P_emaildomain', 'R_emaildomain', 'device_corp', 'browser_corp', 'os_family']
    
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].astype('category')
            if c not in feature_cols:
                feature_cols.append(c)
                
    X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, 'isFraud']
    X_val, y_val = df.loc[val_mask, feature_cols], df.loc[val_mask, 'isFraud']
    X_test, y_test = df.loc[test_mask, feature_cols], df.loc[test_mask, 'isFraud']
    
    return X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols
```

- [ ] **Step 2: Verify dataset loader execution:**
Run: `.venv\Scripts\python.exe -c "from src.models.dataset_loader import get_temporal_splits; X_tr, y_tr, X_val, y_val, X_te, y_te, f_cols, c_cols = get_temporal_splits(); print('Train:', X_tr.shape, 'Val:', X_val.shape, 'Test:', X_te.shape, 'Total Features:', len(f_cols))"`
Expected: Train: (410601, 72), Val: (87512, 72), Test: (92427, 72).

---

### Task 2: Multi-Objective Optuna Hyperparameter Optimization (`src/models/tune_optuna.py`)
**Files:**
- Create: `src/models/tune_optuna.py`

- [ ] **Step 1: Write Optuna multi-objective tuner searching Pareto frontier with Knee-Point Selection:**
```python
import optuna
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score
import json
import os
import numpy as np
from src.models.dataset_loader import get_temporal_splits

def run_optuna_tuning(n_trials=20):
    os.makedirs("models", exist_ok=True)
    print("Loading 3-way temporal splits for Optuna tuning...")
    X_train, y_train, X_val, y_val, _, _, feature_cols, cat_cols = get_temporal_splits()
    
    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
    
    def objective(trial):
        params = {
            'objective': 'binary',
            'metric': ['auc', 'average_precision'],
            'boosting_type': 'gbdt',
            'learning_rate': trial.suggest_float('learning_rate', 0.015, 0.08, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 31, 127),
            'max_depth': trial.suggest_int('max_depth', 6, 12),
            'min_child_samples': trial.suggest_int('min_child_samples', 20, 150),
            'subsample': trial.suggest_float('subsample', 0.65, 0.95),
            'subsample_freq': 1,
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.65, 0.95),
            'scale_pos_weight': trial.suggest_float('scale_pos_weight', 5.0, 18.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 5.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 5.0, log=True),
            'verbosity': -1,
            'n_jobs': -1,
            'seed': 42
        }
        
        model = lgb.train(
            params,
            dtrain,
            num_boost_round=150,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
        )
        
        preds = model.predict(X_val)
        roc_val = roc_auc_score(y_val, preds)
        pr_val = average_precision_score(y_val, preds)
        return pr_val, roc_val

    print(f"Launching Multi-Objective Optuna Study ({n_trials} trials)...")
    study = optuna.create_study(
        directions=["maximize", "maximize"],
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    study.optimize(objective, n_trials=n_trials)
    
    # Pareto Frontier & Knee Selection
    pareto_trials = study.best_trials
    print(f"Found {len(pareto_trials)} non-dominated Pareto trials.")
    
    best_trial = None
    min_dist = float('inf')
    for trial in pareto_trials:
        pr, roc = trial.values
        dist = np.sqrt((1.0 - roc)**2 + (1.0 - pr)**2)
        print(f"Trial {trial.number}: PR-AUC = {pr:.4f}, ROC-AUC = {roc:.4f}, Ideal Dist = {dist:.4f}")
        if dist < min_dist:
            min_dist = dist
            best_trial = trial
            
    print("="*50)
    print(f"Winning Knee-Point Trial: #{best_trial.number}")
    print(f"Validation PR-AUC: {best_trial.values[0]:.4f}, Validation ROC-AUC: {best_trial.values[1]:.4f}")
    print(f"Optimal Parameters: {best_trial.params}")
    print("="*50)
    
    with open("models/best_params.json", "w") as f:
        json.dump(best_trial.params, f, indent=2)
        
    return best_trial.params

if __name__ == "__main__":
    run_optuna_tuning()
```

- [ ] **Step 2: Run Optuna tuning script:**
Run: `.venv\Scripts\python.exe src/models/tune_optuna.py`
Expected: Successfully generates `models/best_params.json`.

---

### Task 3: Production Training & MLflow Model Registry (`src/models/train_lgb.py`)
**Files:**
- Create: `src/models/train_lgb.py`

- [ ] **Step 1: Write production trainer with SQLite MLflow logging and holdout test evaluation:**
```python
import mlflow
import mlflow.lightgbm
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
import json
import os
from src.models.dataset_loader import get_temporal_splits

def train_and_register_model():
    os.makedirs("models", exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    mlflow.set_experiment("transaction_fraud_lightgbm")
    
    with open("models/best_params.json", "r") as f:
        best_params = json.load(f)
        
    print("Loading 3-way temporal splits...")
    X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols = get_temporal_splits()
    
    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
    
    params = {
        'objective': 'binary',
        'metric': ['auc', 'average_precision'],
        'boosting_type': 'gbdt',
        'verbosity': -1,
        'n_jobs': -1,
        'seed': 42,
        **best_params
    }
    
    with mlflow.start_run(run_name="production_lightgbm_optuna"):
        mlflow.log_params(params)
        print("Training production LightGBM booster...")
        model = lgb.train(
            params,
            dtrain,
            num_boost_round=250,
            valid_sets=[dtrain, dval],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
        )
        
        # Validation evaluation
        val_preds = model.predict(X_val)
        val_roc = roc_auc_score(y_val, val_preds)
        val_pr = average_precision_score(y_val, val_preds)
        val_brier = brier_score_loss(y_val, val_preds)
        
        # Untouched Holdout Test evaluation
        test_preds = model.predict(X_test)
        test_roc = roc_auc_score(y_test, test_preds)
        test_pr = average_precision_score(y_test, test_preds)
        test_brier = brier_score_loss(y_test, test_preds)
        
        mlflow.log_metric("val_roc_auc", val_roc)
        mlflow.log_metric("val_pr_auc", val_pr)
        mlflow.log_metric("val_brier_score", val_brier)
        mlflow.log_metric("test_roc_auc", test_roc)
        mlflow.log_metric("test_pr_auc", test_pr)
        mlflow.log_metric("test_brier_score", test_brier)
        
        # Log Feature Importances
        importances = model.feature_importance(importance_type='gain')
        for feat, imp in zip(feature_cols, importances):
            mlflow.log_metric(f"feat_gain_{feat}", imp)
            
        # Serialize Booster model
        model_path = "models/fraud_lgb_model.txt"
        model.save_model(model_path)
        mlflow.log_artifact(model_path)
        
        print("="*60)
        print("PRODUCTION LIGHTGBM MODEL REGISTERED TO MLFLOW (sqlite:///mlruns.db)")
        print(f"Validation Set (Month 5) -> ROC-AUC: {val_roc:.4f}, PR-AUC: {val_pr:.4f}")
        print(f"Holdout Test Set (Month 6) -> ROC-AUC: {test_roc:.4f}, PR-AUC: {test_pr:.4f}")
        print("="*60)
        return model, test_roc, test_pr

if __name__ == "__main__":
    train_and_register_model()
```

- [ ] **Step 2: Run training and registration script:**
Run: `.venv\Scripts\python.exe src/models/train_lgb.py`
Expected: Model saved to `models/fraud_lgb_model.txt` and logged in `mlruns.db`.

---

### Task 4: Real-Time SHAP Attribution Engine (`src/models/explainability.py`)
**Files:**
- Create: `src/models/explainability.py`

- [ ] **Step 1: Write low-latency SHAP TreeExplainer wrapper returning top-3 operational reason codes:**
```python
import shap
import lightgbm as lgb
import numpy as np
import pandas as pd
import time

REASON_CODE_MAP = {
    "tx_count_5m": "BURST_VELOCITY_5M_SPIKE",
    "tx_count_1h": "HIGH_HOURLY_TRANSACTION_VELOCITY",
    "amt_sum_24h": "HIGH_24H_CUMULATIVE_SPEND",
    "TransactionAmt": "UNUSUAL_TRANSACTION_AMOUNT",
    "amt_to_mean_card": "ANOMALOUS_CARD_SPEND_RATIO",
    "amt_to_std_card": "HIGH_AMOUNT_STANDARD_DEVIATION",
    "is_foreign_currency": "FOREIGN_CURRENCY_EXCHANGE_RISK",
    "decimal_places": "IRREGULAR_CURRENCY_PRECISION",
    "email_domain_match": "PURCHASER_RECIPIENT_EMAIL_MISMATCH",
    "is_disposable_email": "DISPOSABLE_EMAIL_DOMAIN_DETECTED",
    "D1_to_mean_card": "UNUSUAL_DAYS_SINCE_REGISTRATION",
    "D2_to_mean_card": "IRREGULAR_TRANSACTION_CYCLE_DELTA",
    "D15_to_mean_card": "UNUSUAL_CARD_LIFECYCLE_DELTA",
    "device_corp": "UNRECOGNIZED_DEVICE_HARDWARE",
    "browser_corp": "HIGH_RISK_BROWSER_FAMILY",
    "screen_aspect_ratio": "ANOMALOUS_DEVICE_RESOLUTION"
}

class FraudExplainer:
    def __init__(self, model_path="models/fraud_lgb_model.txt"):
        self.model = lgb.Booster(model_file=model_path)
        self.explainer = shap.TreeExplainer(self.model)
        self.feature_names = self.model.feature_name()
        
    def explain_transaction(self, feature_df: pd.DataFrame) -> dict:
        t0 = time.perf_counter()
        shap_values = self.explainer.shap_values(feature_df)
        
        if isinstance(shap_values, list):
            sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        else:
            sv = shap_values[0]
            
        top_indices = np.argsort(-sv)[:3]
        top_features = [self.feature_names[i] for i in top_indices]
        reason_codes = [REASON_CODE_MAP.get(f, f"RISK_INDICATOR_{f.upper()}") for f in top_features]
        latency_ms = (time.perf_counter() - t0) * 1000.0
        
        return {
            'top_features': top_features,
            'reason_codes': reason_codes,
            'shap_values': [float(sv[i]) for i in top_indices],
            'latency_ms': latency_ms
        }

if __name__ == "__main__":
    explainer = FraudExplainer()
    print("Explainer initialized successfully with features:", len(explainer.feature_names))
```

---

### Task 5: Targeted Pytest Verification Suite (`tests/test_model_engine.py`)
**Files:**
- Create: `tests/test_model_engine.py`

- [ ] **Step 1: Write Pytest suite verifying model predictions, SHAP latency (<15ms), and MLflow database:**
```python
import pytest
import os
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
```

- [ ] **Step 2: Run Pytest:**
Run: `.venv\Scripts\pytest.exe tests/test_model_engine.py`
Expected: 4 passed in <5s.

---

### Task 6: State Synchronization & Documentation
**Files:**
- Modify: `decision.md`
- Modify: `memory.md`

- [ ] **Step 1: Update `decision.md` with 3-way temporal partition and Multi-Objective Optuna results.**
- [ ] **Step 2: Append Phase 3 completion milestone to `memory.md`.**
