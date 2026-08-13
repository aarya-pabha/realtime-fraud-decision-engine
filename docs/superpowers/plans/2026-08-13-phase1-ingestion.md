/# Phase 1 Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data pipeline to download the Kaggle IEEE dataset and ingest it into DuckDB using a strict Bronze staging layer and Quarantine (DLQ) pattern for referential integrity.

**Architecture:** Python scripts orchestrated locally. Kaggle CLI downloads data. DuckDB reads raw CSVs into VARCHAR staging tables, validates strict types, and routes malformed records to quarantine tables while maintaining identity-transaction referential integrity. 

**Tech Stack:** Python 3.11, `kaggle`, `duckdb`, `pytest`

**Agent Execution Rules:**
1. **Ponytail**: Always apply the `/ponytail` skill. Write the absolute minimum code to make tests pass. No over-engineering.
2. **Context7**: Before writing implementation code, use the Context7 MCP server (`resolve-library-id` and `query-docs`) to check for the latest `duckdb` and `pytest` syntax and best practices.

---

### Task 0: Environment Setup

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create Virtual Environment and Install Dependencies**

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
echo "duckdb\nkaggle\npytest\n" > requirements.txt
pip install -r requirements.txt
```

- [ ] **Step 2: Commit Requirements**

```bash
git add requirements.txt
git commit -m "chore: setup virtual environment and requirements"
```

---

### Task 1: Data Acquisition Script

**Files:**
- Create: `data_pipeline/download_ieee.py`
- Create: `tests/data_pipeline/test_download.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/data_pipeline/test_download.py
import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent dir to path so we can import data_pipeline
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from data_pipeline.download_ieee import download_dataset

@patch('subprocess.run')
@patch('zipfile.ZipFile')
def test_download_dataset_calls_kaggle_and_unzips(mock_zip, mock_run):
    # Setup mock to not crash
    mock_run.return_value = MagicMock(returncode=0)
    
    # Run the function
    download_dataset(output_dir='data/raw')
    
    # Verify kaggle CLI was called
    mock_run.assert_any_call(
        ['kaggle', 'competitions', 'download', '-c', 'ieee-fraud-detection', '-p', 'data/raw'],
        check=True
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_pipeline/test_download.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'data_pipeline.download_ieee'"

- [ ] **Step 3: Write minimal implementation**

```python
# data_pipeline/download_ieee.py
import subprocess
import os
import zipfile

def download_dataset(output_dir: str = 'data/raw'):
    """Downloads the IEEE-CIS dataset via Kaggle API and extracts it."""
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Downloading IEEE dataset to {output_dir}...")
    try:
        subprocess.run(
            ['kaggle', 'competitions', 'download', '-c', 'ieee-fraud-detection', '-p', output_dir],
            check=True
        )
    except FileNotFoundError:
        raise RuntimeError("Kaggle CLI not found. Please install kaggle and set up ~/.kaggle/kaggle.json")
    
    # Unzip the main file
    zip_path = os.path.join(output_dir, 'ieee-fraud-detection.zip')
    if os.path.exists(zip_path):
        print(f"Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print("Extraction complete.")

if __name__ == "__main__":
    download_dataset()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_pipeline/test_download.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/data_pipeline/test_download.py data_pipeline/download_ieee.py
git commit -m "feat(ingestion): add Kaggle dataset downloader script"
```

---

### Task 2: DuckDB Ingestion & Quarantine Pattern

**Files:**
- Create: `data_pipeline/ingest_to_duckdb.py`
- Create: `tests/data_pipeline/test_ingest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/data_pipeline/test_ingest.py
import pytest
import duckdb
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from data_pipeline.ingest_to_duckdb import ingest_csvs_to_duckdb

def test_quarantine_pattern_moves_corrupt_records(tmp_path):
    # Setup tiny mock CSVs
    db_path = tmp_path / "test.duckdb"
    tx_csv = tmp_path / "train_transaction.csv"
    id_csv = tmp_path / "train_identity.csv"
    
    # Transaction: 1 valid, 1 corrupt (TransactionID = 'ABC')
    tx_csv.write_text("TransactionID,TransactionDT,TransactionAmt\n100,86400,50.0\nABC,86400,10.0\n")
    # Identity: 1 for valid, 1 for corrupt
    id_csv.write_text("TransactionID,DeviceType\n100,mobile\nABC,desktop\n")
    
    # Run ingestion
    ingest_csvs_to_duckdb(
        db_path=str(db_path),
        transaction_csv=str(tx_csv),
        identity_csv=str(id_csv)
    )
    
    # Verify tables
    con = duckdb.connect(str(db_path))
    valid_tx = con.execute("SELECT TransactionID FROM valid_transaction").fetchall()
    quar_tx = con.execute("SELECT TransactionID FROM quarantine_transaction").fetchall()
    quar_id = con.execute("SELECT TransactionID FROM quarantine_identity").fetchall()
    
    assert len(valid_tx) == 1
    assert valid_tx[0][0] == '100'
    assert len(quar_tx) == 1
    assert quar_tx[0][0] == 'ABC'
    # Check referential integrity (ABC moved to quarantine_identity)
    assert len(quar_id) == 1
    assert quar_id[0][0] == 'ABC'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_pipeline/test_ingest.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'data_pipeline.ingest_to_duckdb'"

- [ ] **Step 3: Write minimal implementation**

```python
# data_pipeline/ingest_to_duckdb.py
import duckdb

def ingest_csvs_to_duckdb(db_path: str, transaction_csv: str, identity_csv: str):
    """Loads CSVs into DuckDB, segregating corrupt records into quarantine tables."""
    con = duckdb.connect(db_path)
    
    # 1. Load into staging as VARCHAR to avoid crashes
    con.execute(f"CREATE TABLE staging_transaction AS SELECT * FROM read_csv_auto('{transaction_csv}', all_varchar=true)")
    con.execute(f"CREATE TABLE staging_identity AS SELECT * FROM read_csv_auto('{identity_csv}', all_varchar=true)")
    
    # 2. Identify Corrupt Transactions (Cannot cast TransactionID to INTEGER)
    con.execute("""
        CREATE TABLE quarantine_transaction AS 
        SELECT * FROM staging_transaction 
        WHERE try_cast(TransactionID AS INTEGER) IS NULL
    """)
    
    # 3. Save Valid Transactions and create Synthetic Timestamp
    con.execute("""
        CREATE TABLE valid_transaction AS 
        SELECT *, 
        timestamp '2017-12-01 00:00:00' + interval (TRY_CAST(TransactionDT AS BIGINT)) second AS event_timestamp
        FROM staging_transaction 
        WHERE try_cast(TransactionID AS INTEGER) IS NOT NULL
    """)
    
    # 4. Enforce Referential Integrity for Identity Table
    con.execute("""
        CREATE TABLE quarantine_identity AS 
        SELECT * FROM staging_identity 
        WHERE try_cast(TransactionID AS INTEGER) IS NULL
           OR TransactionID IN (SELECT TransactionID FROM quarantine_transaction)
    """)
    
    con.execute("""
        CREATE TABLE valid_identity AS 
        SELECT * FROM staging_identity 
        WHERE TransactionID NOT IN (SELECT TransactionID FROM quarantine_identity)
    """)
    
    # 5. Cleanup Staging
    con.execute("DROP TABLE staging_transaction")
    con.execute("DROP TABLE staging_identity")
    con.close()

if __name__ == "__main__":
    ingest_csvs_to_duckdb(
        db_path='data/offline_store.duckdb',
        transaction_csv='data/raw/train_transaction.csv',
        identity_csv='data/raw/train_identity.csv'
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_pipeline/test_ingest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/data_pipeline/test_ingest.py data_pipeline/ingest_to_duckdb.py
git commit -m "feat(ingestion): implement DuckDB ingestion with DLQ quarantine pattern"
```
