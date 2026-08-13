import duckdb
import os

def ingest_data(db_path: str = 'feature_store.duckdb', raw_dir: str = 'data/raw', tx_types: dict = None, id_types: dict = None):
    """Ingests raw CSV data into DuckDB with a Dead Letter Queue (DLQ) for bad rows."""
    print(f"Connecting to DuckDB at {db_path}...")
    conn = duckdb.connect(db_path)
    
    tx_csv = os.path.join(raw_dir, 'train_transaction.csv')
    id_csv = os.path.join(raw_dir, 'train_identity.csv')
    
    print("Ingesting transaction data with quarantine pattern...")
    tx_type_str = f", types={tx_types}" if tx_types else ""
    conn.execute(f"CREATE TABLE IF NOT EXISTS transactions AS SELECT * FROM read_csv('{tx_csv}', auto_detect=true, store_rejects=true{tx_type_str})")
    
    print("Ingesting identity data...")
    id_type_str = f", types={id_types}" if id_types else ""
    conn.execute(f"CREATE TABLE IF NOT EXISTS identities AS SELECT * FROM read_csv('{id_csv}', auto_detect=true, store_rejects=true{id_type_str})")
    
    print("Saving bad rows to quarantine_log...")
    # reject_errors is a temporary table created by store_rejects=true. We persist it to our DLQ table.
    # Note: If no errors occurred, reject_errors might not exist. We can check if it exists first.
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS quarantine_log AS SELECT * FROM reject_errors")
    except duckdb.CatalogException:
        pass # No rejects were generated
        
    print("Data ingestion complete.")
    conn.close()

if __name__ == "__main__":
    ingest_data()
