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

### [COMPLETED] Phase 5: Real-Time Scoring Microservice (FastAPI + Redis Hydration)
- [x] `src/api/main.py`: FastAPI app initialization with lifespan pre-warming, CORS, and request timing middleware
- [x] `src/api/schemas.py`: Pydantic V2 validated transaction payload, dynamic scoring response, and feedback schemas
- [x] `src/api/feature_service.py`: Feast Redis online store hydration with non-blocking fallback and sub-1ms transform
- [x] `src/api/routes/scoring.py`: POST `/v1/score` (sub-15ms unified LightGBM inference, C++ TreeSHAP attribution, and Bayesian dynamic routing)
- [x] `src/api/routes/feedback.py`: POST `/v1/feedback` & GET `/v1/feedback/stats` (SQLite buffered chargeback label ingestion)
- [x] `src/api/routes/health.py`: GET `/v1/health` & GET `/` (liveness, readiness, and API metadata)
- [x] `tests/test_api.py`: FastAPI TestClient integration test suite (8/8 tests passing, verifying SLA latency, Pydantic V2 config, and logic)

### [COMPLETED] Phase 6: Streaming Ingest (Redpanda) & Interactive Analyst Workbench (Dash / Plotly)
- [x] `src/streaming/producer.py`: Real-time transaction publisher streaming to Redpanda topic `transactions.incoming` with in-memory fallback
- [x] `src/streaming/consumer.py`: Consumer microservice scoring transactions, maintaining ring buffer, and publishing alerts to `transactions.alerts`
- [x] `src/frontend/drift_service.py`: Evidently AI drift service monitoring Wasserstein distances against delayed analyst feedback
- [x] `src/frontend/app.py`: High-performance Dash/Plotly Analyst Workbench (live stream ticker, 3DS interactive checkout simulator, Evidently AI drift monitoring)
- [x] `tests/test_streaming_and_frontend.py`: Integration test suite (4/4 tests passing, 27/27 repository total)

### [COMPLETED] Phase 7: Orchestration & Empirical SLA Load Benchmark (Docker Compose & Locust)
*Branch: `feature/phase7-orchestration-load-benchmark`*
- [x] `requirements.txt`: Add `locust>=2.31.0` and split dev/test tooling to `requirements-dev.txt`
- [x] `tests/locustfile.py`: Low-overhead Locust benchmark using `FastHttpUser` (Context7 verified) stressing `POST /v1/score`
- [x] `tests/run_load_test.py`: Headless benchmark runner asserting contractual SLA ($p95 < 25.0\text{ms}$, $p99 < 45.0\text{ms}$, $0.0\%$ failures) and exporting `reports/locust_sla_report.html` (Novelty #4)
- [x] `docker/Dockerfile.api`: Self-contained multi-stage `python:3.11-slim` image with bundled LightGBM model, DuckDB feature store, jemalloc, and Uvicorn 2-worker concurrency
- [x] `docker/Dockerfile.frontend`: Multi-stage `node:20-alpine` + `nginx:alpine` image serving React Tasko dashboard and reverse-proxying `/v1` with upstream keepalive 32 connection pooling
- [x] `docker-compose.yml`: Multi-container orchestration (Redis 7, Redpanda Kafka, FastAPI engine, React dashboard) on `fraud-net` bridge with chained healthchecks
- [x] Docker Container SLA Verification: Verified sub-25ms p95 latency (<23ms p95, <29ms p99, 0.00% failures) on live multi-container deployment
- [ ] Post-Phase 7 Transition: Return to React dashboard to execute user's final UI design refinements


