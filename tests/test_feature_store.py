import pytest
import duckdb
import pandas as pd
import os

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
    # Event 2 at 10:02:00 -> 1 prior tx (10:00:00)
    assert res.loc[1, 'tx_count_5m'] == 1
    # Event 3 at 10:04:00 -> 2 prior tx (10:00:00, 10:02:00)
    assert res.loc[2, 'tx_count_5m'] == 2
    # Event 4 at 10:20:00 -> 0 prior tx within last 5m (10:15:00 to 10:19:59)
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

def test_parquet_feature_store_integrity():
    """
    Asserts that the exported feature store Parquet table is populated with valid columns.
    """
    parquet_path = "data/features/card_base_features.parquet"
    assert os.path.exists(parquet_path), "Parquet backing store does not exist!"
    
    con = duckdb.connect(":memory:")
    df = con.execute(f"SELECT * FROM '{parquet_path}' LIMIT 10").fetchdf()
    
    required_cols = {"card_base_id", "event_timestamp", "created_timestamp", "tx_count_5m", "tx_count_1h", "amt_sum_24h"}
    assert required_cols.issubset(set(df.columns)), f"Missing required columns in {parquet_path}"
    assert len(df) > 0, "Parquet file is empty!"
