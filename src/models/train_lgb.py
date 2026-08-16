import sys
import os
sys.path.insert(0, os.path.abspath("."))

import mlflow
import mlflow.lightgbm
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
import json
import numpy as np
from src.models.dataset_loader import get_temporal_splits

def train_and_register_model():
    """
    Trains the final production LightGBM booster using winning Optuna parameters.
    Evaluates on untouched Month 6 holdout test set and logs experiment runs to local SQLite MLflow registry (mlruns.db).
    """
    os.makedirs("models", exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///mlruns.db")
    mlflow.set_experiment("transaction_fraud_lightgbm")
    
    params_path = "models/best_params.json"
    if not os.path.exists(params_path):
        raise FileNotFoundError("models/best_params.json not found! Run tune_optuna.py first.")
        
    with open(params_path, "r") as f:
        best_params = json.load(f)
        
    print("Loading 3-way temporal splits (Train: Days 1-120, Val: Days 121-150, Test: Days 151-183)...")
    X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols = get_temporal_splits()
    
    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
    
    params = {
        'objective': 'binary',
        'metric': ['auc', 'average_precision'],
        'boosting_type': 'gbdt',
        'verbosity': -1,
        'n_jobs': -1,
        'seed': 42,
        **best_params
    }
    
    with mlflow.start_run(run_name="production_lightgbm_optuna"):
        mlflow.log_params(params)
        print("Training production LightGBM booster on 410k transactions...")
        model = lgb.train(
            params,
            dtrain,
            num_boost_round=250,
            valid_sets=[dtrain, dval],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
        )
        
        # 1. Validation Horizon Evaluation (Month 5)
        val_preds = model.predict(X_val)
        val_roc = roc_auc_score(y_val, val_preds)
        val_pr = average_precision_score(y_val, val_preds)
        val_brier = brier_score_loss(y_val, val_preds)
        val_loss = log_loss(y_val, val_preds)
        
        # 2. Holdout Test Horizon Evaluation (Month 6 - Untouched)
        test_preds = model.predict(X_test)
        test_roc = roc_auc_score(y_test, test_preds)
        test_pr = average_precision_score(y_test, test_preds)
        test_brier = brier_score_loss(y_test, test_preds)
        test_loss = log_loss(y_test, test_preds)
        
        # Log to MLflow
        mlflow.log_metric("val_roc_auc", val_roc)
        mlflow.log_metric("val_pr_auc", val_pr)
        mlflow.log_metric("val_brier_score", val_brier)
        mlflow.log_metric("val_log_loss", val_loss)
        
        mlflow.log_metric("test_roc_auc", test_roc)
        mlflow.log_metric("test_pr_auc", test_pr)
        mlflow.log_metric("test_brier_score", test_brier)
        mlflow.log_metric("test_log_loss", test_loss)
        
        # Log Feature Importances
        importances = model.feature_importance(importance_type='gain')
        for feat, imp in zip(feature_cols, importances):
            mlflow.log_metric(f"gain_{feat}", imp)
            
        # Serialize model artifact
        model_path = "models/fraud_lgb_model.txt"
        model.save_model(model_path)
        mlflow.log_artifact(model_path)
        
        print("="*65)
        print("PRODUCTION LIGHTGBM MODEL REGISTERED TO MLFLOW (sqlite:///mlruns.db)")
        print(f"Validation Horizon (Month 5) -> ROC-AUC: {val_roc:.4f}, PR-AUC: {val_pr:.4f}")
        print(f"Holdout Test Set   (Month 6) -> ROC-AUC: {test_roc:.4f}, PR-AUC: {test_pr:.4f}")
        print(f"Test Set Brier Score (Calibration): {test_brier:.4f}")
        print(f"Model Artifact Saved: {model_path}")
        print("="*65)
        
        return model, test_roc, test_pr

if __name__ == "__main__":
    train_and_register_model()
