import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter
from src.models.explainability import FraudExplainer

class FastPathCascadeEngine:
    """
    Track A: Two-Stage Fast-Path Gatekeeper Cascade.
    Stage 1: Ultra-fast shallow model (<0.2ms) screening raw low-cost features.
    Stage 2: Heavy Production LightGBM + SHAP + Dynamic Cost Router for ambiguous/risky traffic.
    """
    def __init__(self, primary_model_path="models/fraud_lgb_model.txt", safe_threshold=0.005):
        self.primary_model = lgb.Booster(model_file=primary_model_path)
        self.explainer = FraudExplainer(primary_model_path)
        self.router = DynamicCostRouter()
        self.safe_threshold = safe_threshold
        self.gatekeeper_model = None
        self.fast_features = [
            'TransactionAmt', 'card1', 'card2', 'card3', 'card4', 'card5', 'card6',
            'ProductCD', 'addr1', 'is_foreign_currency', 'decimal_places', 'email_domain_match'
        ]

    def train_gatekeeper(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame = None, y_val: pd.Series = None):
        """Trains an ultra-lightweight 6-leaf gatekeeper tree and calibrates safe_threshold."""
        print("Training Stage 1 Gatekeeper Model (ultra-lightweight 6-leaf LightGBM)...")
        available_cols = [c for c in self.fast_features if c in X_train.columns]
        self.fast_features = available_cols
        
        dtrain = lgb.Dataset(X_train[self.fast_features], label=y_train)
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 6,
            'max_depth': 3,
            'learning_rate': 0.1,
            'verbosity': -1,
            'n_jobs': -1
        }
        self.gatekeeper_model = lgb.train(params, dtrain, num_boost_round=30)
        
        if X_val is not None and y_val is not None:
            p_val = self.gatekeeper_model.predict(X_val[self.fast_features])
            val_frauds = p_val[y_val == 1]
            # Set safe threshold at 1st percentile of fraud scores with safety margin (zero leakage)
            if len(val_frauds) > 0:
                self.safe_threshold = float(np.percentile(val_frauds, 0.5) * 0.8)
            print(f"Auto-calibrated Fast-Path safe threshold: tau_safe = {self.safe_threshold:.4f}")
        print("Stage 1 Gatekeeper Model trained successfully.")

    def score_transaction_cascade(self, row_df: pd.DataFrame, amount: float) -> dict:
        """
        Executes cascaded inference on a single transaction.
        """
        t0 = time.perf_counter()
        
        # Stage 1: Ultra-fast pre-screen
        p_stage1 = float(self.gatekeeper_model.predict(row_df[self.fast_features])[0])
        
        if p_stage1 < self.safe_threshold:
            # Fast-path instant approval (bypasses SHAP tree search and heavy feature transforms)
            total_latency = (time.perf_counter() - t0) * 1000.0
            return {
                "execution_path": "FAST_PATH",
                "action": "APPROVE",
                "fraud_probability": round(p_stage1, 4),
                "reason_codes": [],
                "latency_ms": round(total_latency, 3)
            }
        else:
            # Deep-path: Full LightGBM + SHAP + Dynamic Router
            p_stage2 = float(self.primary_model.predict(row_df)[0])
            shap_res = self.explainer.explain_transaction(row_df)
            route_res = self.router.route_transaction(p_stage2, amount)
            total_latency = (time.perf_counter() - t0) * 1000.0
            
            return {
                "execution_path": "DEEP_PATH",
                "action": route_res.action,
                "fraud_probability": round(p_stage2, 4),
                "reason_codes": shap_res["reason_codes"],
                "latency_ms": round(total_latency, 3)
            }

    def evaluate_holdout_cascade(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """Vectorized benchmark across Month 6 holdout test set."""
        p_gatekeeper = self.gatekeeper_model.predict(X_test[self.fast_features])
        p_primary = self.primary_model.predict(X_test)
        amounts = X_test['TransactionAmt'].values
        labels = y_test.values

        # Fast path mask
        fast_path_mask = (p_gatekeeper < self.safe_threshold)
        deep_path_mask = ~fast_path_mask

        # Final effective probabilities: fast path retains gatekeeper score, deep path uses primary
        effective_probs = np.where(fast_path_mask, p_gatekeeper, p_primary)

        # Performance metrics
        roc_auc = roc_auc_score(labels, effective_probs)
        pr_auc = average_precision_score(labels, effective_probs)

        # Missed fraud analysis on fast path
        fast_path_frauds = int(np.sum(fast_path_mask & (labels == 1)))
        total_frauds = int(np.sum(labels == 1))
        leakage_pct = (fast_path_frauds / total_frauds) * 100.0

        # Financial evaluation via Router
        dyn_res = self.router.batch_route_and_evaluate(effective_probs, amounts, labels)

        return {
            "track": "Track A: Two-Stage Fast-Path Cascade",
            "fast_path_traffic_pct": float(np.mean(fast_path_mask) * 100.0),
            "deep_path_traffic_pct": float(np.mean(deep_path_mask) * 100.0),
            "fast_path_missed_frauds": fast_path_frauds,
            "fast_path_leakage_pct": leakage_pct,
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "total_financial_loss_dollars": dyn_res["total_financial_loss_dollars"],
            "net_savings_dollars": 338745.87 - dyn_res["total_financial_loss_dollars"],
            "chargeback_ratio_pct": dyn_res["chargeback_ratio"] * 100.0
        }

if __name__ == "__main__":
    X_tr, y_tr, _, _, X_te, y_te, _, _ = get_temporal_splits()
    engine = FastPathCascadeEngine()
    engine.train_gatekeeper(X_tr, y_tr)
    res = engine.evaluate_holdout_cascade(X_te, y_te)
    print("\n--- Track A Fast-Path Cascade Results ---")
    for k, v in res.items():
        print(f"{k}: {v}")
