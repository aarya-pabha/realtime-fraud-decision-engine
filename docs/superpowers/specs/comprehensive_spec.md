# Transaction Fraud Engine - Comprehensive Phased Specification

*This document serves as the granular, technical master specification for the Real-Time Transaction Fraud Engine. It is written in phases, ensuring that detailed technical designs for downstream phases adapt to the realities discovered during earlier implementations.*

## Phase 1: Ingestion & Offline Store

### 1. Data Acquisition (`data_pipeline/download_ieee.py`)
- **Purpose**: Authenticate with Kaggle and download the raw IEEE-CIS Fraud Detection dataset securely and reproducibly.
- **Data Flow**: `Kaggle API` -> `data/raw/`
- **Technical Details**:
  - Requires `kaggle.json` in the user's `~/.kaggle/` directory.
  - Script will use the `kaggle` python package (`kaggle competitions download -c ieee-fraud-detection`).
  - Automatically unzips `train_transaction.csv` and `train_identity.csv`.
- **Error Handling**: Graceful exit if Kaggle token is missing, providing instructions to the user.

### 2. DuckDB Ingestion & Quarantine Pattern (`data_pipeline/ingest_to_duckdb.py`)
- **Purpose**: Load massive CSVs into DuckDB, enforce strict typing, generate Feast-compatible timestamps, and isolate corrupt data for review.
- **Architecture**:
  - **Staging (Bronze)**: Load CSVs into temporary staging tables (`staging_transaction`, `staging_identity`) using `read_csv` with generic `VARCHAR` parsing. This ensures DuckDB never crashes on unexpected formats.
  - **Validation & Quarantine**: Attempt strict casting of critical columns (e.g., `TransactionID` to INTEGER, `TransactionAmt` to DOUBLE). Rows that fail validation are routed to `quarantine_transaction` or `quarantine_identity` tables. Valid rows are routed to `valid_transaction` and `valid_identity`.
  - **Referential Integrity**: Execute a cross-check join. If a `TransactionID` exists in `quarantine_transaction`, its corresponding record in `valid_identity` (if present) is moved to `quarantine_identity`. The reverse applies if an identity record is quarantined.
  - **Timestamp Synthesis**: Feast requires a proper `event_timestamp`. The script adds the `TransactionDT` (seconds) to a baseline date (`2017-12-01 00:00:00`) to generate a real `DATETIME` column.
- **Output**: Generates `data/offline_store.duckdb` containing the valid tables (`transactions`, `identity`) and quarantine tables (`quarantine_transaction`, `quarantine_identity`).

---

## Phase 2: Dual-Tier Feature Store & Point-in-Time Temporal Join Engine

### 1. Offline Temporal Velocity Engine (`src/features/point_in_time.py`)
- **Purpose**: Computes zero-leakage sliding window velocity features directly inside DuckDB using native SQL window functions, guaranteeing that feature calculations strictly use data prior to each transaction's event timestamp.
- **Timestamp Synthesis**:
  - `event_timestamp = TIMESTAMP '2017-12-01 00:00:00' + INTERVAL (TransactionDT) SECOND`
  - `created_timestamp = NOW()`
- **Dual-Tier Entity Key Construction**:
  - `card_base_id`: Universal key `CONCAT_WS('_', card1, COALESCE(card2, 0), COALESCE(card3, 0), COALESCE(card4, 'unk'), COALESCE(card5, 0), COALESCE(card6, 'unk'))` (14,893 unique entities, 100% coverage).
  - `cardholder_uid`: Strict identity key `CONCAT_WS('_', card_base_id, COALESCE(CAST(addr1 AS VARCHAR), 'NONE_' || CAST(TransactionID AS VARCHAR)), COALESCE(P_emaildomain, 'NONE_' || CAST(TransactionID AS VARCHAR)))` (234,720 unique entities, 0 false collisions).
- **DuckDB Window Aggregations (Zero Leakage)**:
  - `tx_count_5m`: `COUNT(*) OVER (PARTITION BY card_base_id ORDER BY event_timestamp RANGE BETWEEN INTERVAL 5 MINUTE PRECEDING AND INTERVAL 1 SECOND PRECEDING)`
  - `tx_count_1h`: `COUNT(*) OVER (PARTITION BY card_base_id ORDER BY event_timestamp RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING)`
  - `amt_sum_24h`: `COALESCE(SUM(TransactionAmt) OVER (PARTITION BY card_base_id ORDER BY event_timestamp RANGE BETWEEN INTERVAL 24 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING), 0.0)`
  - `distinct_merchants_1h`: `COUNT(DISTINCT P_emaildomain) OVER (PARTITION BY card_base_id ORDER BY event_timestamp RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING)`
- **Output Storage**:
  - DuckDB tables `card_base_features`, `cardholder_features`, and `transaction_context_features` materialized in `feature_store.duckdb` and exported as parquet files under `data/features/`.

### 2. Feast Feature Repository (`feature_repo/`)
- **Configuration (`feature_repo/feature_store.yaml`)**:
  ```yaml
  project: transaction_fraud_store
  registry: data/registry.db
  provider: local
  offline_store:
    type: duckdb
  online_store:
    type: redis
    connection_string: localhost:6379
  ```
- **Entity Definitions (`feature_repo/entities.py`)**:
  - `card_base_id`: Join key `card_base_id`
  - `cardholder_uid`: Join key `cardholder_uid`
- **Feature Views (`feature_repo/feature_views.py`)**:
  - `card_velocity_feature_view`: Backed by `card_base_features` with TTL of 30 days. Contains rolling counts, amount aggregations, and scaled D-deltas.
  - `cardholder_feature_view`: Backed by `cardholder_features` with TTL of 30 days. Contains frequency encodings.
  - `transaction_context_feature_view`: Backed by `transaction_context_features`. Contains diurnal, currency, email, device, and 33 V-medoids.

### 3. Point-in-Time Join Demonstration (`src/features/generate_training_dataset.py`)
- **Purpose**: Calls `store.get_historical_features(entity_df, features)` to build the production training matrix using exact AS-OF temporal joins.
- **Verification**: Mathematically verifies that features at timestamp $T$ never contain information from transactions occurring at $T_{future} \ge T$.

### 4. Targeted Pytest Suite (`tests/test_feature_store.py`)
- **Test 1 (`test_zero_leakage_temporal_join`)**: Asserts that synthetic future transactions injected after timestamp $T$ do not alter historical feature values at $T$.
- **Test 2 (`test_entity_null_address_isolation`)**: Asserts that distinct transactions with missing addresses never cross-contaminate entity velocity.
- **Test 3 (`test_feature_view_schema_compatibility`)**: Asserts all 72 features align with Feast schema types (`Float32`, `Int32`, `String`).

---

## Phase 3: Model Engine (LightGBM Tuning with Optuna & MLflow Registry)

### 1. Dataset & Temporal Partitioning (`src/models/train_lgb.py`)
- **Full Scope Dataset**: Complete 590,540 rows utilizing the 72 validated domain features.
- **Strict Temporal Split**:
  - **Training Set**: Days 1 to 120 (`TransactionDT < 120 * 86400`) -> 410,601 transactions.
  - **Holdout Validation Set**: Days 121 to 183 (`TransactionDT >= 120 * 86400`) -> 179,939 transactions.
  - Zero cross-contamination or look-ahead leakage across temporal horizons.

### 2. Optuna Hyperparameter Optimization (`src/models/tune_optuna.py`)
- **Objective**: Maximize Out-of-Time **PR-AUC (Average Precision)** while tracking ROC-AUC.
- **Search Space**:
  - `learning_rate`: `[0.01, 0.1]` (log scale)
  - `num_leaves`: `[31, 255]`
  - `max_depth`: `[5, 12]`
  - `min_child_samples`: `[20, 300]`
  - `subsample` (bagging fraction): `[0.6, 1.0]`
  - `colsample_bytree` (feature fraction): `[0.6, 1.0]`
  - `scale_pos_weight`: `[5.0, 20.0]` (handles 3.50% class imbalance)
  - `reg_alpha` (L1), `reg_lambda` (L2): `[1e-3, 10.0]` (log scale)
- **Early Stopping**: 25 boosting rounds without validation metric improvement.

### 3. MLflow Experiment & Model Registry (`src/models/train_lgb.py`)
- **Backend**: Local SQLite database at `sqlite:///mlruns.db` (zero external container overhead per `GEMINI.md`).
- **Experiment**: `transaction_fraud_lightgbm`.
- **Logged Entities**:
  - Full hyperparameter config (`best_params`).
  - Validation metrics: `oot_roc_auc`, `oot_pr_auc`, `brier_score`, `log_loss`.
  - Feature importance metrics for all 72 features.
  - Model artifact: Serialized LightGBM Booster (`models/fraud_lgb_model.txt` and MLflow model packaging).

### 4. Real-Time SHAP Reason Code Generator (`src/models/explainability.py`)
- **TreeExplainer Engine**: Initialized on trained Booster for sub-10ms localized attribution.
- **Reason Code Dictionary**: Maps top-3 positive Shapley contribution feature indices into domain explanations:
  - `amt_to_mean_card` / `TransactionAmt` -> `UNUSUAL_TRANSACTION_AMOUNT`
  - `tx_count_5m` / `tx_count_1h` -> `HIGH_VELOCITY_BURST`
  - `is_foreign_currency` / `decimal_places` -> `FOREIGN_CURRENCY_ANOMALY`
  - `email_domain_match` / `is_disposable_email` -> `SUSPICIOUS_EMAIL_DOMAIN`
  - `D1_to_mean_card` / `D2_to_mean_card` -> `UNUSUAL_CARD_LIFECYCLE_DELTA`
  - `device_corp` / `screen_aspect_ratio` -> `RISKY_DEVICE_FINGERPRINT`
- **Output Schema**: Returns top-3 reason codes, baseline expected value, and individual feature contributions.

### 5. Verification Suite (`tests/test_model_engine.py`)
- **Test 1 (`test_model_prediction_range`)**: Asserts model probabilities $\in [0, 1]$ and strictly monotonic with risk.
- **Test 2 (`test_shap_reason_codes_latency_and_format`)**: Asserts SHAP reason code generation runs in $<15\text{ms}$ and yields exactly 3 non-empty valid codes.
- **Test 3 (`test_mlflow_run_logged`)**: Asserts experiment run and metrics are successfully stored in `mlruns.db`.

---

## Phase 4: Dynamic Transaction-Value Aware Cost Matrix Router (`src/models/cost_router.py`)

### 1. Mathematical Objective & Asymmetric Loss Matrix
- **Expected Financial Loss Optimization**: Replaces arbitrary static thresholds ($\tau = 0.50$) with dynamic thresholding $\tau^*(\text{TransactionAmt})$ derived from Bayesian Decision Theory.
- **Cost Parameters (2026 Payments Standard)**:
  - $C_{\text{FN}}(\text{Amt}) = \text{TransactionAmt} + \$25.00$ (Direct principal fraud loss + chargeback dispute fee)
  - $C_{\text{FP}}(\text{Amt}) = (\text{TransactionAmt} \times 0.02) + \$5.00$ (Lost interchange margin + customer support churn penalty)
  - $C_{\text{TP}} = \$0.00$, $C_{\text{TN}} = \$0.00$
  - $C_{\text{step\_up}} = \$0.05$ (EMV 3DS 2.0 authentication cost)
- **Dynamic Theoretical Cutoff**:
  $$\tau^*(\text{Amt}) = \frac{C_{\text{FP}}(\text{Amt})}{C_{\text{FP}}(\text{Amt}) + C_{\text{FN}}(\text{Amt})} = \frac{0.02 \cdot \text{Amt} + 5.00}{1.02 \cdot \text{Amt} + 30.00}$$

### 2. Tri-State Operational Routing Decisions
- **`APPROVE`**: $P(\text{Fraud}) < \tau_{\text{step\_up}}(\text{Amt}) = \text{clip}(\tau^*(\text{Amt}), 0.03, 0.25)$ (Frictionless flow)
- **`STEP_UP_3DS`**: $\tau_{\text{step\_up}}(\text{Amt}) \le P(\text{Fraud}) < \tau_{\text{decline}}(\text{Amt}) = \text{clip}(4.0 \cdot \tau^*(\text{Amt}), 0.35, 0.80)$ (SMS OTP Challenge: 85% legit resolution, 95% fraud block)
- **`DECLINE`**: $P(\text{Fraud}) \ge \tau_{\text{decline}}(\text{Amt})$ (Hard block)


### 3. Financial Benchmark Simulator (`src/models/evaluate_cost_router.py`)
- Evaluates complete **Month 6 Holdout Test Set ($92,453$ transactions)**.
- Compares Total Dollar Loss ($), Net Savings ($), and Visa VAMP / Mastercard ECP chargeback compliance across:
  1. Policy A: Naive Approve-All ($\tau = 1.0$)
  2. Policy B: Standard Static ML Cutoff ($\tau = 0.50$)
  3. Policy C: Optimal Tuned Static Cutoff ($\tau = \tau_{\text{static\_opt}}$)
  4. Policy D: Dynamic Value-Aware Cost Router (Novelty #2)

### 4. Verification Suite (`tests/test_router.py`)
- **Test 1 (`test_monotonicity_with_amount`)**: Proves $\tau^*(A_1) > \tau^*(A_2)$ for $A_1 < A_2$.
- **Test 2 (`test_threshold_bounds_and_clamping`)**: Asserts mathematical safety bounds.
- **Test 3 (`test_micro_vs_high_value_routing_behavior`)**: Confirms adaptive risk sensitivity.
- **Test 4 (`test_sub_millisecond_routing_latency`)**: Asserts execution latency $< 1.0\text{ms}$.
- **Test 5 (`test_dynamic_router_outperforms_static_baseline`)**: Proves net dollar loss reduction.

---

## Phase 5: Real-Time Scoring Microservice (FastAPI + Redis Online Hydration)

### 1. Architecture & Lifespan Pre-Warming (`src/api/main.py`)
- **FastAPI Lifespan Context Manager**: Loads LightGBM booster (`models/fraud_lgb_model.txt`), pre-warms native TreeSHAP explainer, initializes `FeatureService`, and prepares `DynamicCostRouter` singletons during startup to eliminate cold-start overhead.
- **Middleware**: Injects `CORSMiddleware` and microsecond `X-Process-Time-Ms` custom latency headers.

### 2. Pydantic Schemas (`src/api/schemas.py`)
- **`TransactionPayload`**: Pydantic V2 strictly typed schema for raw payment attributes, card BINs, identity hashes, and D-deltas.
- **`ScoringResponse`**: Structured decisioning output containing `action` ("APPROVE", "STEP_UP_3DS", "DECLINE"), `fraud_probability`, `expected_cost_dollars`, top-3 `reason_codes`, dynamic `thresholds`, and sub-component `latency` breakdown.
- **`FeedbackPayload` & `FeedbackResponse`**: Schema for analyst chargeback/dispute label ingestion.
- **`HealthResponse`**: Liveness probe payload.

### 3. Sub-5ms Online Feature Hydration (`src/api/feature_service.py`)
- **Dual-Tier Entity Resolution**: Dynamically constructs `card_base_id` and `cardholder_uid`.
- **Non-Blocking Online Retrieval**: Pings Redis on startup. Retrieves `tx_count_5m`, `tx_count_1h`, and `amt_sum_24h` from Feast online store if active; gracefully falls back to sub-millisecond local streaming feature synthesis when Redis is offline.

### 4. Endpoints & Unified Inference (`src/api/routes/`)
- **`POST /v1/score`**: Executes unified LightGBM inference & native C++ TreeSHAP attribution via `pred_contrib=True`, computes calibrated sigmoid probability, extracts top-3 reason codes, and applies Bayesian dynamic cost routing in $<25\text{ms}$.
- **`POST /v1/feedback`**: Ingests ground-truth analyst dispute resolutions and persists them to SQLite buffer `data/feedback_store.sqlite` for downstream drift monitoring.
- **`GET /v1/health` & `GET /`**: System health and API metadata probes.

### 5. Verification Suite (`tests/test_api.py`)
- Complete integration test suite verifying 200 OK responses, low-risk `APPROVE`, high-risk `DECLINE`, borderline `STEP_UP_3DS`, $<25\text{ms}$ latency budget, feedback ingestion, and 422 validation handling.

---

## Phase 6: Streaming Ingest (Redpanda) & Interactive Analyst Workbench (Dash / Plotly)

### 1. High-Throughput Streaming Engine (`src/streaming/`)
- **Transaction Stream Publisher (`src/streaming/producer.py`)**: Reads temporal holdout stream and publishes JSON events to Redpanda Kafka topic `transactions.incoming` with realistic replay speed.
- **Consumer Microservice (`src/streaming/consumer.py`)**: Consumes incoming events, hydrates features, executes scoring via `/v1/score`, and routes high-risk transactions to `transactions.alerts` topic.

### 2. Interactive Analyst Workbench (`src/frontend/app.py`)
- **Framework**: Dash / Plotly with custom Vanilla CSS design.
- **Components**:
  1. **Live Transaction Ticker**: Real-time streaming table with color-coded actions (`APPROVE` in emerald, `STEP_UP_3DS` in amber, `DECLINE` in crimson).
  2. **Interactive 3DS Checkout Simulator**: Allows analysts to adjust transaction amount ($10 to $5,000) and feature sliders to visualize dynamic threshold adaptation and SHAP reason code attributions in real time.
  3. **Evidently AI Drift Monitoring Dashboard**: Visualizes data drift (Wasserstein distance) and prediction drift on analyst feedback batches from `/v1/feedback`.

---

*(Phase 7 and 8 specifications will be appended upon completion of Phase 6.)*

