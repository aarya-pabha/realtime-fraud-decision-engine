import os
import duckdb
import pandas as pd
from feast import FeatureStore

def generate_historical_training_matrix(repo_path="feature_repo", db_path="feature_store.duckdb"):
    """
    Demonstrates zero-leakage temporal point-in-time feature retrieval using Feast.
    Joins rolling velocity features with historical transaction events based strictly on timestamp.
    """
    print(f"1. Loading FeatureStore from {repo_path}...")
    store = FeatureStore(repo_path=repo_path)
    
    print("2. Fetching sample transaction events from DuckDB...")
    con = duckdb.connect(db_path, read_only=True)
    entity_df = con.execute("""
    SELECT 
        card_base_id,
        event_timestamp,
        TransactionID,
        isFraud,
        TransactionAmt
    FROM enriched_transactions
    ORDER BY event_timestamp ASC
    LIMIT 100;
    """).fetchdf()
    con.close()
    
    print(f"Sample Entity DataFrame shape: {entity_df.shape}")
    print("3. Executing Feast Point-in-Time Historical Join...")
    
    training_data = store.get_historical_features(
        entity_df=entity_df,
        features=[
            "card_velocity_features:tx_count_5m",
            "card_velocity_features:tx_count_1h",
            "card_velocity_features:amt_sum_24h",
        ]
    ).to_df()
    
    print("4. Point-in-Time Temporal Join Successful! Sample output:")
    print(training_data[["TransactionID", "event_timestamp", "card_base_id", "tx_count_5m", "tx_count_1h", "amt_sum_24h"]].head(10))
    return training_data

if __name__ == "__main__":
    generate_historical_training_matrix()
