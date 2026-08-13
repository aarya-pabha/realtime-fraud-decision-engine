# Real-Time Transaction Fraud Engine

Implementation of a production-grade fraud detection platform using the IEEE-CIS dataset, Redpanda (Kafka), DuckDB, Feast, Redis, LightGBM, FastAPI, and Dash.

## User Review Required
> [!IMPORTANT]
> - **Dataset Size**: As requested, we will use the entire unmodified IEEE-CIS dataset (approx. 590k transactions). Training will take slightly longer but will demonstrate true Big Data scalability for your portfolio.
> - **Local Infrastructure**: We will provision local Docker containers for Redpanda (Kafka) and Redis to keep the project completely free and self-contained on your machine.
> - **MLflow**: We will use a lightweight local SQLite database (`mlruns.db`) to track experiments instead of a heavy Postgres container.
> - **Orchestration & Testing**: We will use standard Python scripts (`python ingest.py`) instead of Airflow/Prefect. Testing will be high-impact: Locust for API load tests, and targeted Pytest cases for critical components (Feature Store & Dynamic Router).

## Open Questions
None. We successfully resolved all remaining design dependencies via the second grilling session (Orchestration, MLflow Backend, Testing Strategy).

## Proposed Changes

### 1. Ingestion & Offline Store (DuckDB)
#### [NEW] `data_pipeline/download_ieee.py` (Kaggle API script for dataset)
#### [NEW] `data_pipeline/ingest_to_duckdb.py` (Loads raw CSVs and builds point-in-time tables)

### 2. Feature Store (Feast + Redis)
#### [NEW] `feature_repo/feature_views.py` (Defines sliding window velocity and identity features)
#### [NEW] `feature_repo/feature_store.yaml` (Feast config pointing to DuckDB offline and Redis online)

### 3. Model Training (LightGBM)
#### [NEW] `training/train_lgb.py` (Fetches historical features from Feast, trains LightGBM, logs to MLflow)

### 4. Real-Time API (FastAPI)
#### [NEW] `api/main.py` (FastAPI app, fetches from Redis via Feast, calculates SHAP reason codes)
#### [NEW] `api/cost_router.py` (Dynamic thresholding logic based on transaction amount)

### 5. Frontend Dashboard (Dash/Plotly)
#### [NEW] `frontend/app.py` (Dash UI for the Analyst Workbench and Customer Checkout Simulation)

### 6. Streaming Pipeline (Redpanda)
#### [NEW] `streaming/producer.py` (Simulates real-time transactions by publishing to a Redpanda topic)
#### [NEW] `streaming/consumer.py` (Consumes transactions, triggers FastAPI scoring, updates dashboards)

### 7. Orchestration & Load Testing
#### [NEW] `docker-compose.yml` (Spins up Redpanda and Redis)
#### [NEW] `tests/locustfile.py` (Load testing script for API SLAs)
#### [NEW] `tests/test_feature_store.py` (Pytest for point-in-time logic)
#### [NEW] `tests/test_router.py` (Pytest for dynamic thresholding logic)
#### [NEW] `requirements.txt`

## Verification Plan

### Automated Tests
- Run `pytest tests/` to verify core ML engineering logic.
- Run `locust -f tests/locustfile.py` to ensure the FastAPI `/v1/score` endpoint maintains sub-25ms p95 latency under load.

### Manual Verification
1. Start infrastructure via `docker-compose up -d`.
2. Run data pipeline scripts and `feast materialize` to load Redis.
3. Run `training/train_lgb.py` and verify the model artifact is saved.
4. Launch the FastAPI server and the Dash frontend.
5. Run the streaming producer and verify that transactions appear in real-time on the Dash frontend with SHAP reason codes and correct routing actions (Approve/Decline/Step-Up).
