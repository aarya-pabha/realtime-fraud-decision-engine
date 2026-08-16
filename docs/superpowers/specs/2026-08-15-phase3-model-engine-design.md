# Technical Design Specification: Phase 3 Model Engine & Explainability Platform

* **Document Path:** `docs/superpowers/specs/2026-08-15-phase3-model-engine-design.md`
* **Status:** Complete & Validated
* **Target Release:** Phase 3 of Real-Time Transaction Fraud Detection Platform
* **Authors:** AI Assistant & Lead ML Engineer

---

## 1. Executive Summary & Objective

The Phase 3 Model Engine delivers the machine learning inference core and experiment tracking infrastructure for the real-time fraud detection platform. Building upon the 72 validated domain features engineered in Phase 2, this engine:
1. Implements a rigorous **3-way temporal partition** (Train, Validation, Holdout Test) across the 183-day IEEE-CIS dataset to prevent data leakage and validation overfitting.
2. Automates **Multi-Objective Hyperparameter Optimization (Optuna)** to simultaneously maximize Out-of-Time Area Under Precision-Recall Curve ($\text{PR-AUC}$) and Area Under ROC Curve ($\text{ROC-AUC}$).
3. Extracts the non-dominated **Pareto Frontier** and automatically selects the operational model using **Knee-Point Euclidean Distance** to the ideal point $(1.0, 1.0)$.
4. Manages the complete ML lifecycle with **MLflow** using an embedded, containerless SQLite backend (`sqlite:///mlruns.db`).
5. Generates **sub-10ms localized feature attributions (TreeSHAP)** and translates Shapley contributions into human-readable fraud reason codes for automated decisioning and human analyst review.

---

## 2. Temporal Partitioning Strategy (Zero-Leakage 3-Way Split)

To ensure zero temporal look-ahead bias and eliminate validation selection leakage, the 183-day labeled dataset (590,540 rows) is partitioned chronologically:

```
0 ──────────── Day 120 ─────────── Day 151 ─────────── Day 183
│   TRAINING SET      │  VALIDATION SET   │   HOLDOUT TEST SET   │
│   (Months 1 to 4)   │     (Month 5)     │      (Month 6)       │
│   ~410,601 rows     │   ~90,000 rows    │    ~89,939 rows      │
│                     │                   │                      │
│ • Fit tree splits   │ • Optuna tuning   │ • Untouched holdout  │
│ • Base weights      │ • Early stopping  │ • Final benchmark    │
│                     │ • Knee selection  │ • Streaming replay   │
```

* **Train Set ($\text{Days } 1 \le t < 120$):** $410,601$ transactions ($\sim 69.5\%$ of dataset). Used exclusively to fit tree nodes and compute leaf values.
* **Validation Set ($\text{Days } 120 \le t < 151$):** $\sim 90,000$ transactions ($\sim 15.2\%$ of dataset). Used exclusively by Optuna to evaluate trial configurations, monitor early stopping, and extract the Pareto frontier.
* **Holdout Test Set ($\text{Days } 151 \le t \le 183$):** $\sim 89,939$ transactions ($\sim 15.2\%$ of dataset). **Completely untouched** during model tuning and training. Evaluates final generalization performance, calibrates the Phase 4 Dynamic Cost Router, and supplies transaction events for the Phase 6 streaming simulation.

---

## 3. Multi-Objective Hyperparameter Optimization (Optuna)

### 3.1. Formulation
Because the dataset exhibits a severe class imbalance ($3.50\%$ fraud rate), optimizing a single metric introduces operational trade-offs:
* Optimizing **only ROC-AUC** yields high macro-separation but elevated false alarm rates in top-tier alert buckets.
* Optimizing **only PR-AUC** risks over-specializing on dense, obvious fraud clusters at the expense of general rank-ordering.

Optuna is configured with a multi-objective search:
$$\text{Maximize } f_1(\theta) = \text{PR-AUC}_{\text{val}}, \quad \text{Maximize } f_2(\theta) = \text{ROC-AUC}_{\text{val}}$$

### 3.2. Hyperparameter Search Space

```python
def sample_hyperparameters(trial: optuna.Trial) -> dict:
    return {
        "objective": "binary",
        "metric": ["auc", "average_precision"],
        "boosting_type": "gbdt",
        "learning_rate": trial.suggest_float("learning_rate", 0.015, 0.08, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 31, 127),
        "max_depth": trial.suggest_int("max_depth", 6, 12),
        "min_child_samples": trial.suggest_int("min_child_samples", 20, 150),
        "subsample": trial.suggest_float("subsample", 0.65, 0.95),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.95),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 5.0, 18.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 5.0, log=True),
        "verbosity": -1,
        "n_jobs": -1,
        "seed": 42
    }
```

### 3.3. Automated Knee-Point Selection
From the set of non-dominated Pareto trials $\mathcal{P}$, the production winning trial $\theta^*$ is selected by minimizing the normalized Euclidean distance to the ideal coordinate $(1.0, 1.0)$:

$$\theta^* = \arg\min_{\theta \in \mathcal{P}} \sqrt{(1.0 - \text{ROC-AUC}_{\text{val}}(\theta))^2 + (1.0 - \text{PR-AUC}_{\text{val}}(\theta))^2}$$

The winning configuration is exported to `models/best_params.json`.

---

## 4. MLflow Experiment Tracking & Model Packaging

Per the repository guidelines (`GEMINI.md`), MLflow is configured with a lightweight local SQLite database (`sqlite:///mlruns.db`) and local filesystem artifact storage (`mlruns/`), eliminating Docker/Postgres container overhead.

### Logged Metadata:
* **Parameters:** Full hyperparameter set from `best_params.json`.
* **Validation Metrics (Month 5):** `val_roc_auc`, `val_pr_auc`, `val_log_loss`, `val_brier_score`.
* **Holdout Test Metrics (Month 6):** `test_roc_auc`, `test_pr_auc`, `test_brier_score`, `test_log_loss`.
* **Feature Importances:** Split count and Information Gain for all 72 features.
* **Artifacts:**
  * Native serialized booster: `models/fraud_lgb_model.txt`.
  * Packaged MLflow model with signature and input schema.

---

## 5. Real-Time SHAP Reason Code Generator (`src/models/explainability.py`)

### 5.1. Low-Latency Attribution Engine
* Uses `shap.TreeExplainer(booster)` optimized for LightGBM decision trees.
* Capable of evaluating individual transaction vectors in $<10\text{ms}$ on standard CPU hardware.

### 5.2. Operational Reason Code Mapping Dictionary
The top 3 positive Shapley contribution features are translated into standardized banking risk attribution codes:

```python
REASON_CODE_MAP = {
    # Velocity & Burst Attacks
    "tx_count_5m": "BURST_VELOCITY_5M_SPIKE",
    "tx_count_1h": "HIGH_HOURLY_TRANSACTION_VELOCITY",
    
    # Amount Volatility & Sizing
    "TransactionAmt": "UNUSUAL_TRANSACTION_AMOUNT",
    "amt_to_mean_card": "ANOMALOUS_CARD_SPEND_RATIO",
    "amt_to_std_card": "HIGH_AMOUNT_STANDARD_DEVIATION",
    
    # Currency & Geographic Anomalies
    "is_foreign_currency": "FOREIGN_CURRENCY_EXCHANGE_RISK",
    "decimal_places": "IRREGULAR_CURRENCY_PRECISION",
    
    # Email & Identity Risk
    "email_domain_match": "PURCHASER_RECIPIENT_EMAIL_MISMATCH",
    "is_disposable_email": "DISPOSABLE_EMAIL_DOMAIN_DETECTED",
    
    # Card Lifecycle Deltas
    "D1_to_mean_card": "UNUSUAL_DAYS_SINCE_REGISTRATION",
    "D2_to_mean_card": "IRREGULAR_TRANSACTION_CYCLE_DELTA",
    
    # Device & Technical Fingerprints
    "device_corp": "UNRECOGNIZED_DEVICE_HARDWARE",
    "browser_corp": "HIGH_RISK_BROWSER_FAMILY",
    "screen_aspect_ratio": "ANOMALOUS_DEVICE_RESOLUTION"
}
```

If a contributing feature is not in the explicit map, the engine falls back to `RISK_INDICATOR_<FEATURE_NAME_UPPERCASE>`.

---

## 6. Project Directory Scaffolding for Phase 3

```
Transaction-Fraud/
├── feature_repo/                      # Feast repository (from Phase 2)
│   ├── feature_definitions.py
│   └── feature_store.yaml
├── models/                            # Serialized model artifacts
│   ├── best_params.json               # Winning Optuna hyperparameter set
│   └── fraud_lgb_model.txt            # Serialized LightGBM Booster
├── src/
│   ├── features/                      # Feature pipeline (from Phase 2)
│   │   ├── point_in_time.py
│   │   └── generate_training_dataset.py
│   └── models/                        # Model Engine (Phase 3)
│       ├── dataset_loader.py          # 3-Way temporal partition loader
│       ├── tune_optuna.py             # Multi-objective Optuna tuner
│       ├── train_lgb.py               # Production trainer & MLflow logger
│       └── explainability.py          # Real-time SHAP reason code generator
├── tests/
│   ├── test_feature_store.py          # Phase 2 tests (passing)
│   └── test_model_engine.py           # Phase 3 tests (Inference, SHAP, MLflow)
├── mlruns.db                          # Embedded SQLite MLflow backend
└── requirements.txt
```

---

## 7. Verification & Automated Pytest Suite

Automated verification in `tests/test_model_engine.py` validates 3 critical SLA and correctness gates:

1. **`test_model_prediction_range`:** Asserts probability outputs $\in [0.0, 1.0]$, checks monotonicity against known high-risk feature values.
2. **`test_shap_reason_codes_latency_and_format`:** Asserts `FraudExplainer.explain_transaction()` executes in $<15\text{ms}$ and yields exactly 3 non-empty string codes with associated positive Shapley contributions.
3. **`test_mlflow_run_logged`:** Asserts that an active experiment run exists in `mlruns.db` containing `oot_roc_auc` and `oot_pr_auc` metrics.
