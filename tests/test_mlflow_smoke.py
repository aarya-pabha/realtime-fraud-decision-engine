import sys
import os
sys.path.insert(0, os.path.abspath("."))

import mlflow
import sqlite3
import pandas as pd

def test_mlflow_sqlite_integration():
    print("Testing MLflow SQLite tracking backend...")
    db_uri = "sqlite:///mlruns.db"
    mlflow.set_tracking_uri(db_uri)
    experiment_name = "test_smoke_experiment"
    mlflow.set_experiment(experiment_name)
    
    with mlflow.start_run(run_name="smoke_test_run") as run:
        run_id = run.info.run_id
        # Log sample params
        mlflow.log_params({
            "learning_rate": 0.064,
            "num_leaves": 105,
            "smoke_test": True
        })
        
        # Log sample metrics
        mlflow.log_metrics({
            "test_roc_auc": 0.9166,
            "test_pr_auc": 0.5507,
            "test_brier_score": 0.0245
        })
        
        # Create and log dummy artifact
        os.makedirs("models", exist_ok=True)
        dummy_file = "models/smoke_test_artifact.txt"
        with open(dummy_file, "w") as f:
            f.write("MLflow integration verification OK\n")
        mlflow.log_artifact(dummy_file)
        
    print(f"Run {run_id} logged successfully.")
    
    # Verify directly inside SQLite database
    con = sqlite3.connect("mlruns.db")
    runs_df = pd.read_sql(f"SELECT * FROM runs WHERE run_uuid = '{run_id}'", con)
    params_df = pd.read_sql(f"SELECT * FROM params WHERE run_uuid = '{run_id}'", con)
    metrics_df = pd.read_sql(f"SELECT * FROM metrics WHERE run_uuid = '{run_id}'", con)
    con.close()
    
    assert len(runs_df) == 1, "Run was not found in SQLite runs table!"
    assert len(params_df) == 3, f"Expected 3 params, found {len(params_df)}"
    assert len(metrics_df) == 3, f"Expected 3 metrics, found {len(metrics_df)}"
    
    print("="*60)
    print("MLFLOW SQLITE TRACKING VERIFIED 100% OPERATIONAL")
    print("Logged Metrics in SQLite DB:")
    for _, row in metrics_df.iterrows():
        print(f"  • {row['key']}: {row['value']}")
    print("="*60)

if __name__ == "__main__":
    test_mlflow_sqlite_integration()
