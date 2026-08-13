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
*(Phase 2 through 7 specifications will be brainstormed and appended here upon the completion of Phase 1 to prevent premature optimization.)*
