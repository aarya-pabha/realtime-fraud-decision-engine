import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, average_precision_score

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter

class UnsupervisedOutlierEngine:
    """
    Track C: Hybrid Unsupervised Outlier Scorer (Isolation Forest).
    Identifies zero-day high-ticket behavioral anomalies without historical fraud labels.
    """
    def __init__(self, primary_model_path="models/fraud_lgb_model.txt"):
        self.lgb_model = lgb.Booster(model_file=primary_model_path)
        self.iso_forest = None
        self.router = DynamicCostRouter()
        self.numeric_features = [
            'TransactionAmt', 'log_TransactionAmt', 'amt_to_mean_card', 'amt_to_std_card',
            'D1_to_mean_card', 'D2_to_mean_card', 'D15_to_mean_card', 'decimal_places',
            'is_foreign_currency', 'tx_count_5m', 'tx_count_1h', 'amt_sum_24h'
        ]

    def fit_isolation_forest(self, X_train: pd.DataFrame):
        """Fits a high-speed Isolation Forest on behavioral spend and velocity representations."""
        print("Fitting Unsupervised Isolation Forest (100 estimators, max_samples=10000)...")
        available_cols = [c for c in self.numeric_features if c in X_train.columns]
        self.numeric_features = available_cols
        
        # Impute NaNs with median for isolation forest
        train_mat = X_train[self.numeric_features].fillna(X_train[self.numeric_features].median())
        self.medians = X_train[self.numeric_features].median()

        self.iso_forest = IsolationForest(
            n_estimators=100,
            max_samples=10000,
            contamination=0.035, # Prior fraud prevalence
            random_state=42,
            n_jobs=-1
        )
        self.iso_forest.fit(train_mat)
        print("Isolation Forest fitted successfully.")

    def compute_anomaly_scores(self, X_df: pd.DataFrame) -> np.ndarray:
        """Computes normalized anomaly score in range [0, 1]."""
        mat = X_df[self.numeric_features].fillna(self.medians)
        # decision_function returns negative for outliers, positive for inliers
        raw_scores = -self.iso_forest.decision_function(mat)
        # Min-max normalization
        norm_scores = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-8)
        return norm_scores

    def evaluate_holdout_outlier(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """Evaluates unsupervised outlier detector and hybrid fusion on Month 6 holdout test set."""
        p_lgb = self.lgb_model.predict(X_test)
        s_outlier = self.compute_anomaly_scores(X_test)
        labels = y_test.values
        amounts = X_test['TransactionAmt'].values

        # 1. Pure Isolation Forest Metrics
        iso_roc = roc_auc_score(labels, s_outlier)
        iso_pr = average_precision_score(labels, s_outlier)

        # High-value fraud recall (Spend > $1,000)
        high_mask = (amounts >= 1000.0)
        high_labels = labels[high_mask]
        high_outlier_scores = s_outlier[high_mask]
        high_lgb_scores = p_lgb[high_mask]

        top_10pct_threshold_iso = np.percentile(s_outlier, 90)
        high_fraud_caught_iso = np.sum((high_outlier_scores >= top_10pct_threshold_iso) & (high_labels == 1))
        total_high_fraud = np.sum(high_labels == 1)
        iso_high_recall = (high_fraud_caught_iso / total_high_fraud) * 100.0 if total_high_fraud > 0 else 0.0

        # 2. Hybrid Score Fusion: P_hybrid = 0.85 * P_lgb + 0.15 * S_outlier
        p_hybrid = (0.85 * p_lgb) + (0.15 * s_outlier)
        hybrid_roc = roc_auc_score(labels, p_hybrid)
        hybrid_pr = average_precision_score(labels, p_hybrid)

        dyn_res = self.router.batch_route_and_evaluate(p_hybrid, amounts, labels)

        return {
            "track": "Track C: Hybrid Unsupervised Outlier Scorer",
            "iso_forest_standalone_roc_auc": float(iso_roc),
            "iso_forest_standalone_pr_auc": float(iso_pr),
            "high_value_fraud_recall_pct": float(iso_high_recall),
            "hybrid_fused_roc_auc": float(hybrid_roc),
            "hybrid_fused_pr_auc": float(hybrid_pr),
            "total_financial_loss_dollars": dyn_res["total_financial_loss_dollars"],
            "net_savings_dollars": 338745.87 - dyn_res["total_financial_loss_dollars"],
            "chargeback_ratio_pct": dyn_res["chargeback_ratio"] * 100.0
        }

if __name__ == "__main__":
    X_tr, y_tr, _, _, X_te, y_te, _, _ = get_temporal_splits()
    engine = UnsupervisedOutlierEngine()
    engine.fit_isolation_forest(X_tr)
    res = engine.evaluate_holdout_outlier(X_te, y_te)
    print("\n--- Track C Unsupervised Outlier Results ---")
    for k, v in res.items():
        print(f"{k}: {v}")
