import duckdb
import os

def build_offline_feature_tables(db_path="feature_store.duckdb", output_dir="data/features"):
    """
    Computes zero-leakage sliding window velocity features using pure DuckDB SQL.
    Guarantees feature calculation uses ONLY records strictly prior to current transaction timestamp.
    Validated via Context7 documentation for DuckDB interval window framing and Parquet export.
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Connecting to DuckDB at {db_path}...")
    con = duckdb.connect(db_path)
    
    print("1. Synthesizing timestamps and entity keys...")
    con.execute("""
    CREATE OR REPLACE TABLE enriched_transactions AS
    SELECT 
        t.TransactionID,
        t.isFraud,
        t.TransactionDT,
        TIMESTAMP '2017-12-01 00:00:00' + (t.TransactionDT || ' seconds')::INTERVAL AS event_timestamp,
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
    
    print("2. Computing Zero-Leakage Window Functions for card_base_id...")
    con.execute("""
    CREATE OR REPLACE TABLE card_base_features AS
    SELECT 
        card_base_id,
        event_timestamp,
        created_timestamp,
        -- 5-Minute Velocity Count (strictly preceding: [t - 5m, t - 1s])
        COUNT(*) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 5 MINUTE PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_5m,
        -- 1-Hour Velocity Count (strictly preceding: [t - 1h, t - 1s])
        COUNT(*) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_1h,
        -- 24-Hour Cumulative Spend (strictly preceding: [t - 24h, t - 1s])
        COALESCE(SUM(TransactionAmt) OVER (
            PARTITION BY card_base_id 
            ORDER BY event_timestamp 
            RANGE BETWEEN INTERVAL 24 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ), 0.0) AS amt_sum_24h
    FROM enriched_transactions
    ORDER BY event_timestamp ASC;
    """)
    
    print(f"3. Exporting Parquet backing stores to {output_dir}...")
    card_base_parquet = os.path.join(output_dir, "card_base_features.parquet").replace('\\', '/')
    tx_source_parquet = os.path.join(output_dir, "transactions_source.parquet").replace('\\', '/')
    
    con.execute(f"COPY (SELECT * FROM card_base_features) TO '{card_base_parquet}' (FORMAT PARQUET);")
    con.execute(f"COPY (SELECT * FROM enriched_transactions) TO '{tx_source_parquet}' (FORMAT PARQUET);")
    con.close()
    print("Point-in-time velocity tables materialized and exported to Parquet successfully.")

if __name__ == "__main__":
    build_offline_feature_tables()
