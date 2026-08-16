# Real-Time Transaction Fraud Engine - Implementation Roadmap

Implementation roadmap of the production-grade fraud detection platform using the IEEE-CIS dataset, Redpanda (Kafka), DuckDB, Feast, Redis, LightGBM, FastAPI, and Dash.

---

## Phased Implementation Progress

### [COMPLETED] Phase 1: Ingestion & Offline Store (DuckDB Quarantine DLQ)
- [x] Automated Kaggle dataset acquisition: `data_pipeline/download_ieee.py`
- [x] Strict typing, schema enforcement, and DLQ quarantine routing: `data_pipeline/ingest_duckdb.py`
- [x] Targeted Pytest suite passing: `tests/data_pipeline/`

### [COMPLETED] Phase 2: Dual-Tier Feature Store (DuckDB + Redis via Feast)
- [x] DuckDB zero-leakage sliding window velocity engine (`5m`, `1h`, `24h`): `src/features/point_in_time.py`
- [x] Collision-safe dual-tier entity resolution (`card_base_id`, `cardholder_uid`)
- [x] 33 $V$-medoid feature reduction preserving $>99.6\%$ variance
- [x] Feast feature store repository and AS-OF temporal joins: `feature_repo/`, `src/features/generate_training_dataset.py`
- [x] Targeted Pytest suite passing: `tests/test_feature_store.py`

### [COMPLETED] Phase 3: Model Engine (LightGBM + Optuna + MLflow + SHAP)
- [x] Strict 3-way temporal dataset split (Train: Days 1-120, Val: Days 121-150, Test: Days 151-183): `src/models/dataset_loader.py`
- [x] Multi-Objective Optuna hyperparameter tuning with Knee-Point Euclidean selection: `src/models/tune_optuna.py`
- [x] Production LightGBM training with local SQLite MLflow tracking: `src/models/train_lgb.py`
- [x] Sub-10ms localized SHAP TreeExplainer reason code generator: `src/models/explainability.py`
- [x] Verification suite passing: `tests/test_model_engine.py` (Test ROC-AUC: `0.9003`, Test PR-AUC: `0.5063`)

### [COMPLETED] Phase 4: Dynamic Transaction-Value Aware Cost Matrix Router (Novelty #2)
- [x] 2026 payments benchmarks & Three-Way Decision Theory math proofs: `docs/cost_matrix_and_3ds_research_reference.md`
- [x] Sub-millisecond Bayesian Dynamic Cost Router module ($k = 4.0$): `src/models/cost_router.py`
- [x] Targeted mathematical property Pytest suite passing: `tests/test_router.py`
- [x] Month 6 holdout test set financial benchmark simulator: `src/models/evaluate_cost_router.py` (+$223,508.35 saved / 66.0% ROI / 0.42% chargeback ratio)
- [x] Master evaluation report published: `docs/phase4_dynamic_cost_router_evaluation_report.md`

---

### [NEXT] Phase 5: Real-Time Scoring Microservice (FastAPI + Redis Hydration)
- [ ] `src/api/main.py`: FastAPI app initialization with CORS and logging
- [ ] `src/api/routes/scoring.py`: POST `/v1/score` (sub-15ms endpoint with Redis online feature hydration, LightGBM inference, SHAP reason codes, and dynamic routing)
- [ ] `src/api/routes/feedback.py`: POST `/v1/feedback` (ingests analyst chargeback labels for drift monitoring)
- [ ] `src/api/routes/health.py`: GET `/v1/health` (liveness & readiness probes)
- [ ] `tests/test_api.py`: FastAPI TestClient integration test suite

### [UPCOMING] Phase 6: Streaming Ingest (Redpanda) & Interactive Analyst Workbench (Dash / Plotly)
- [ ] `src/streaming/producer.py`: Real-time transaction publisher streaming to Redpanda topic
- [ ] `src/streaming/consumer.py`: Consumer microservice scoring transactions and publishing alerts
- [ ] `src/frontend/app.py`: High-performance Dash/Plotly Analyst Workbench (live stream, 3DS interactive checkout simulator, Evidently AI drift monitoring)

### [UPCOMING] Phase 7: Orchestration & Empirical SLA Load Benchmark (Docker Compose & Locust)
- [ ] `docker-compose.yml`: Multi-container orchestration (Redpanda, Redis, FastAPI, Dash)
- [ ] `tests/locustfile.py`: Automated Locust stress test asserting sub-25ms p95 latency under 500+ req/sec (Novelty #4)
