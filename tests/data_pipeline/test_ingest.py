import pytest
import duckdb
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from data_pipeline.ingest_duckdb import ingest_data

def test_duckdb_ingestion_creates_tables_and_quarantine(tmp_path):
    # Setup mock CSV data
    db_path = str(tmp_path / "test.duckdb")
    raw_dir = str(tmp_path / "raw")
    os.makedirs(raw_dir)
    
    # Create valid and faulty transaction CSV
    # Using 3 columns: TransactionID, TransactionDT, TransactionAmt
    # We will introduce a faulty row where TransactionAmt is a string instead of a float
    tx_csv = os.path.join(raw_dir, 'train_transaction.csv')
    with open(tx_csv, 'w') as f:
        f.write("TransactionID,TransactionDT,TransactionAmt\n")
        f.write("1,86400,68.5\n")     # Valid
        f.write("2,86401,INVALID\n")  # Faulty: string instead of float for Amt
        f.write("3,86402,150.0\n")    # Valid

    # Create identity CSV (no errors)
    id_csv = os.path.join(raw_dir, 'train_identity.csv')
    with open(id_csv, 'w') as f:
        f.write("TransactionID,DeviceType\n")
        f.write("1,mobile\n")
        
    # Run ingestion with strict typing for the Amt column so it rejects the string
    ingest_data(db_path=db_path, raw_dir=raw_dir, tx_types={'TransactionAmt': 'DOUBLE'})
    
    # Connect and verify
    conn = duckdb.connect(db_path)
    
    # Verify valid data
    tx_res = conn.execute("SELECT * FROM transactions ORDER BY TransactionID").fetchall()
    assert len(tx_res) == 2
    assert tx_res[0][0] == 1
    assert tx_res[1][0] == 3
    
    # Verify quarantine log caught the invalid row
    quarantine_res = conn.execute("SELECT * FROM quarantine_log").fetchall()
    assert len(quarantine_res) == 1
    # Check that it caught row 2 (which had 'INVALID' in TransactionAmt)
    assert 'INVALID' in str(quarantine_res[0])
