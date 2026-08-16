import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import numpy as np
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter

class DualModelBlendEngine:
    """
    Track B: Heterogeneous Dual-Model Ensemble Blend (LightGBM + CatBoost).
    Combines tree-split diversity across gradient boosting frameworks.
    """
    def __init__(self, primary_model_path="models/fraud_lgb_model.txt"):
        self.lgb_model = lgb.Booster(model_file=primary_model_path)
        self.cat_model = None
        self.router = DynamicCostRouter()

    def train_auxiliary_catboost(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series, cat_cols: list):
        """Trains a high-performance lightweight CatBoost classifier."""
        print("Training Auxiliary CatBoost Classifier (depth=6, iterations=200)...")
        
        # Prepare categorical indices / names
        clean_X_tr = X_train.copy()
        clean_X_va = X_val.copy()
        
        # Fill NAs for categoricals to make CatBoost robust
        for c in cat_cols:
            clean_X_tr[c] = clean_X_tr[c].astype(object).fillna("missing").astype(str)
            clean_X_va[c] = clean_X_va[c].astype(object).fillna("missing").astype(str)

        self.cat_cols = cat_cols
        self.cat_model = CatBoostClassifier(
            iterations=150,
            depth=6,
            learning_rate=0.08,
            auto_class_weights='Balanced',
            eval_metric='Logloss',
            random_seed=42,
            verbose=False,
            thread_count=-1
        )
        
        self.cat_model.fit(
            clean_X_tr, y_train,
            cat_features=cat_cols,
            eval_set=(clean_X_va, y_val),
            early_stopping_rounds=20,
            verbose=False
        )
        print("Auxiliary CatBoost model trained successfully.")

    def evaluate_holdout_blend(self, X_test: pd.DataFrame, y_test: pd.Series, weight_lgb=0.70) -> dict:
        """Evaluates ensemble blend on Month 6 holdout test set."""
        clean_X_te = X_test.copy()
        for c in self.cat_cols:
            clean_X_te[c] = clean_X_te[c].astype(object).fillna("missing").astype(str)


        t0 = time.perf_counter()
        p_lgb = self.lgb_model.predict(X_test)
        t_lgb = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        p_cat = self.cat_model.predict_proba(clean_X_te)[:, 1]
        t_cat = (time.perf_counter() - t1) * 1000.0

        p_blend = (weight_lgb * p_lgb) + ((1.0 - weight_lgb) * p_cat)

        labels = y_test.values
        amounts = X_test['TransactionAmt'].values

        roc_auc = roc_auc_score(labels, p_blend)
        pr_auc = average_precision_score(labels, p_blend)
        brier = brier_score_loss(labels, p_blend)

        dyn_res = self.router.batch_route_and_evaluate(p_blend, amounts, labels)

        return {
            "track": f"Track B: Dual-Model Blend ({int(weight_lgb*100)}% LGBM + {int((1-weight_lgb)*100)}% CatBoost)",
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "brier_score": float(brier),
            "lgb_inference_time_ms": t_lgb / len(X_test),
            "cat_inference_time_ms": t_cat / len(X_test),
            "total_inference_time_ms": (t_lgb + t_cat) / len(X_test),
            "total_financial_loss_dollars": dyn_res["total_financial_loss_dollars"],
            "net_savings_dollars": 338745.87 - dyn_res["total_financial_loss_dollars"],
            "chargeback_ratio_pct": dyn_res["chargeback_ratio"] * 100.0
        }

if __name__ == "__main__":
    X_tr, y_tr, X_va, y_va, X_te, y_te, f_cols, c_cols = get_temporal_splits()
    engine = DualModelBlendEngine()
    engine.train_auxiliary_catboost(X_tr, y_tr, X_va, y_va, c_cols)
    res = engine.evaluate_holdout_blend(X_te, y_te, weight_lgb=0.70)
    print("\n--- Track B Dual-Model Blend Results ---")
    for k, v in res.items():
        print(f"{k}: {v}")
