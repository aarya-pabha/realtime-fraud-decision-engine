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
*(Phase 3 through 8 specifications will be appended upon the completion of Phase 2.)*
