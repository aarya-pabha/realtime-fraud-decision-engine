# Phase 2 Implementation Plan: Dual-Tier Feature Store & Point-in-Time Join Engine

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the production-grade Dual-Tier Feature Store (Feast + DuckDB + Redis), implement the zero-leakage sliding window velocity engine in pure DuckDB SQL, define Feast feature views for all 72 validated features, demonstrate point-in-time joins, and write targeted Pytest verification suites.

**Architecture:** 
- **Offline Store (DuckDB):** Ingests and calculates sliding-window velocity aggregations (`5m`, `1h`, `24h`) using temporal window functions with strict `< event_timestamp` boundary (zero future leakage).
- **Online Store (Redis):** Sub-5ms key-value store for serving real-time entity features to FastAPI.
- **Feast Orchestrator:** Manages feature registry, point-in-time temporal joins (`get_historical_features`), and online materialization (`feast materialize`).

**Tech Stack:** Python 3.11 (`.venv`), DuckDB, Feast 0.65, Redis 8.1, Pytest.

---

## Proposed Tasks

### Task 1: Offline Temporal Velocity Engine (`src/features/point_in_time.py`)
**Files:**
- Create: `src/features/point_in_time.py`

- [ ] **Step 1: Write DuckDB SQL Window Aggregations and Parquet Materialization:**
```python
import duckdb
import os

def build_offline_feature_tables(db_path="feature_store.duckdb", output_dir="data/features"):
    """
    Computes zero-leakage sliding window velocity features using pure DuckDB SQL.
    Guarantees feature calculation uses ONLY records strictly prior to current transaction timestamp.
    """
    os.makedirs(output_dir, exist_ok=True)
    con = duckdb.connect(db_path)
    
    # 1. Synthesize timestamps and entity keys
    con.execute("""
    CREATE OR REPLACE TABLE enriched_transactions AS
    SELECT 
        t.TransactionID,
        t.isFraud,
        t.TransactionDT,
        TIMESTAMP '2017-12-01 00:00:00' + INTERVAL (t.TransactionDT) SECOND AS event_timestamp,
        NOW() AS created_timestamp,
        t.TransactionAmt,
        t.ProductCD,
        t.card1, t.card2, t.card3, t.card4, t.card5, t.card6,
        t.addr1, t.addr2,
        t.P_emaildomain, t.R_emaildomain,
        t.D1, t.D2, t.D15,
        -- Universal Card Base Entity Key (100% complete)
        CONCAT_WS('_', t.card1, COALESCE(t.card2, 0), COALESCE(t.card3, 0), COALESCE(t.card4, 'unk'), COALESCE(t.card5, 0), COALESCE(t.card6, 'unk')) AS card_base_id,
        -- Strict Cardholder UID (Zero null collision)
        CONCAT_WS('_', 
            CONCAT_WS('_', t.card1, COALESCE(t.card2, 0), COALESCE(t.card3, 0), COALESCE(t.card4, 'unk'), COALESCE(t.card5, 0), COALESCE(t.card6, 'unk')),
            COALESCE(CAST(t.addr1 AS VARCHAR), 'NONE_' || CAST(t.TransactionID AS VARCHAR)),
            COALESCE(t.P_emaildomain, 'NONE_' || CAST(t.TransactionID AS VARCHAR))
        ) AS cardholder_uid
    FROM transactions t;
    """)
    
    # 2. Compute Zero-Leakage Window Functions for card_base_id
    con.execute("""
    CREATE OR REPLACE TABLE card_base_features AS
    SELECT 
        card_base_id,
        event_timestamp,
        created_timestamp,
        -- 5-Minute Velocity Count (strictly preceding)
        COUNT(*) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 5 MINUTE PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_5m,
        -- 1-Hour Velocity Count (strictly preceding)
        COUNT(*) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_1h,
        -- 24-Hour Spend Sum (strictly preceding)
        COALESCE(SUM(TransactionAmt) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 24 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ), 0.0) AS amt_sum_24h
    FROM enriched_transactions
    ORDER BY event_timestamp ASC;
    """)
    
    # 3. Export to Parquet backing files for Feast
    con.execute(f"COPY card_base_features TO '{output_dir}/card_base_features.parquet' (FORMAT PARQUET);")
    con.execute(f"COPY enriched_transactions TO '{output_dir}/transactions_source.parquet' (FORMAT PARQUET);")
    con.close()
    print("Point-in-time velocity tables materialized and exported to Parquet.")

if __name__ == "__main__":
    build_offline_feature_tables()
```

- [ ] **Step 2: Run script to verify DuckDB window execution:**
Run: `.venv\Scripts\python.exe src/features/point_in_time.py`
Expected: Successfully generates `data/features/card_base_features.parquet` and `data/features/transactions_source.parquet`.

---

### Task 2: Configure Feast Feature Store Repository (`feature_repo/`)
**Files:**
- Create: `feature_repo/feature_store.yaml`
- Create: `feature_repo/entities.py`
- Create: `feature_repo/features.py`

- [ ] **Step 1: Write `feature_repo/feature_store.yaml`:**
```yaml
project: transaction_fraud_store
registry: data/registry.db
provider: local
offline_store:
  type: file
online_store:
  type: redis
  connection_string: localhost:6379
```

- [ ] **Step 2: Write `feature_repo/entities.py`:**
```python
from feast import Entity

card_base_id = Entity(
    name="card_base_id",
    join_keys=["card_base_id"],
    description="Universal card entity identifier for velocity aggregations"
)

cardholder_uid = Entity(
    name="cardholder_uid",
    join_keys=["cardholder_uid"],
    description="Strict cardholder identity identifier"
)
```

- [ ] **Step 3: Write `feature_repo/features.py`:**
```python
from datetime import timedelta
from feast import Field, FeatureView, FileSource
from feast.types import Float32, Int32, Int64, String
from feature_repo.entities import card_base_id

card_base_source = FileSource(
    path="data/features/card_base_features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

card_velocity_fv = FeatureView(
    name="card_velocity_features",
    entities=[card_base_id],
    ttl=timedelta(days=30),
    schema=[
        Field(name="tx_count_5m", dtype=Int64),
        Field(name="tx_count_1h", dtype=Int64),
        Field(name="amt_sum_24h", dtype=Float32),
    ],
    online=True,
    source=card_base_source,
)
```

- [ ] **Step 4: Verify Feast apply:**
Run: `cd feature_repo; ..\.venv\Scripts\feast.exe apply; cd ..`
Expected: Feast registry successfully compiled and saved.

---

### Task 3: Targeted Pytest Verification Suite (`tests/test_feature_store.py`)
**Files:**
- Create: `tests/test_feature_store.py`

- [ ] **Step 1: Write Pytest cases testing Zero-Leakage & Null Isolation:**
```python
import pytest
import duckdb
import pandas as pd
from datetime import datetime, timedelta

def test_zero_leakage_window_functions():
    """
    Asserts that transactions at timestamp T ONLY count previous events (T_prev < T).
    Future events (T_future >= T) MUST NOT contribute to velocity.
    """
    con = duckdb.connect(":memory:")
    con.execute("""
    CREATE TABLE test_tx (
        card_base_id VARCHAR,
        event_timestamp TIMESTAMP,
        amt DOUBLE
    );
    INSERT INTO test_tx VALUES 
    ('card_1', TIMESTAMP '2017-12-01 10:00:00', 100.0),
    ('card_1', TIMESTAMP '2017-12-01 10:02:00', 50.0),
    ('card_1', TIMESTAMP '2017-12-01 10:04:00', 25.0),
    ('card_1', TIMESTAMP '2017-12-01 10:20:00', 300.0);
    """)
    
    res = con.execute("""
    SELECT 
        event_timestamp,
        amt,
        COUNT(*) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 5 MINUTE PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_5m
    FROM test_tx
    ORDER BY event_timestamp;
    """).fetchdf()
    
    # Event 1 at 10:00:00 -> 0 prior tx
    assert res.loc[0, 'tx_count_5m'] == 0
    # Event 2 at 10:02:00 -> 1 prior tx (10:00)
    assert res.loc[1, 'tx_count_5m'] == 1
    # Event 3 at 10:04:00 -> 2 prior tx (10:00, 10:02)
    assert res.loc[2, 'tx_count_5m'] == 2
    # Event 4 at 10:20:00 -> 0 prior tx within last 5m (10:15 to 10:19:59)
    assert res.loc[3, 'tx_count_5m'] == 0

def test_entity_null_address_isolation():
    """
    Asserts that null address transactions are uniquely salted and do not collide.
    """
    df = pd.DataFrame({
        'TransactionID': [101, 102],
        'card1': [1000, 1000],
        'card2': [500, 500],
        'card3': [150, 150],
        'card4': ['visa', 'visa'],
        'card5': [226, 226],
        'card6': ['debit', 'debit'],
        'addr1': [None, None],
        'P_emaildomain': ['gmail.com', 'gmail.com']
    })
    
    # Salting logic
    card_base = df['card1'].astype(str) + '_' + df['card2'].astype(str)
    addr_salt = df['addr1'].fillna('NONE_' + df['TransactionID'].astype(str))
    uid = card_base + '_' + addr_salt
    
    assert uid.nunique() == 2, "Null addresses falsely collided!"
```

- [ ] **Step 2: Run Pytest:**
Run: `.venv\Scripts\pytest.exe tests/test_feature_store.py`
Expected: 2 passed in <1s.

---

### Task 4: Point-in-Time Historical Join Script (`src/features/generate_training_dataset.py`)
**Files:**
- Create: `src/features/generate_training_dataset.py`

- [ ] **Step 1: Write Point-in-Time Join Demonstration Script using Feast:**
```python
import os
import pandas as pd
from feast import FeatureStore

def generate_historical_training_matrix(repo_path="feature_repo"):
    store = FeatureStore(repo_path=repo_path)
    
    # Load sample entity events
    entity_df = pd.DataFrame({
        "card_base_id": ["10000_0_0_unk_0_unk", "10000_0_0_unk_0_unk"],
        "event_timestamp": [
            pd.to_datetime("2017-12-01 12:00:00"),
            pd.to_datetime("2017-12-02 12:00:00")
        ]
    })
    
    print("Executing Feast point-in-time join...")
    training_data = store.get_historical_features(
        entity_df=entity_df,
        features=[
            "card_velocity_features:tx_count_5m",
            "card_velocity_features:tx_count_1h",
            "card_velocity_features:amt_sum_24h"
        ]
    ).to_df()
    
    print("Point-in-Time Join Succeeded:")
    print(training_data.head())
    return training_data

if __name__ == "__main__":
    generate_historical_training_matrix()
```

- [ ] **Step 2: Verify Execution:**
Run: `.venv\Scripts\python.exe src/features/generate_training_dataset.py`
Expected: Returns joined feature matrix with zero errors.

---

### Task 5: State Synchronization & Documentation
**Files:**
- Modify: `decision.md`
- Modify: `memory.md`

- [ ] **Step 1: Update `decision.md` with Feast Dual-Tier configuration and zero-leakage window functions.**
- [ ] **Step 2: Append Phase 2 completion milestone to `memory.md`.**
