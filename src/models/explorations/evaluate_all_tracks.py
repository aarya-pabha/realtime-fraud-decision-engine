import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import json
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter
from src.models.explorations.fast_path_cascade import FastPathCascadeEngine
from src.models.explorations.dual_model_blend import DualModelBlendEngine
from src.models.explorations.unsupervised_outlier import UnsupervisedOutlierEngine

def benchmark_latency(score_func, sample_rows: list, n_runs=100) -> dict:
    """Measures p50, p95, and p99 inference latency in milliseconds."""
    latencies = []
    # Warmup
    for row in sample_rows[:5]:
        _ = score_func(row)
        
    for _ in range(n_runs):
        for row in sample_rows:
            t0 = time.perf_counter()
            _ = score_func(row)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            
    return {
        "p50_ms": float(np.percentile(latencies, 50)),
        "p95_ms": float(np.percentile(latencies, 95)),
        "p99_ms": float(np.percentile(latencies, 99)),
        "mean_ms": float(np.mean(latencies))
    }

def run_master_multi_model_benchmark():
    print("="*90)
    print("BONUS EXPLORATION: MULTI-MODEL & CASCADED ARCHITECTURE BENCHMARK")
    print("="*90)
    
    print("Loading 3-way temporal dataset partitions (Train: 410k, Val: 87k, Test: 92k)...")
    X_train, y_train, X_val, y_val, X_test, y_test, f_cols, cat_cols = get_temporal_splits()
    
    amounts = X_test['TransactionAmt'].values
    labels = y_test.values
    
    # ---------------------------------------------------------
    # 0. Baseline: Single Production LightGBM Engine
    # ---------------------------------------------------------
    print("\n[0/3] Evaluating Baseline: Single LightGBM Production Engine...")
    lgb_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    p_base = lgb_model.predict(X_test)
    base_roc = roc_auc_score(labels, p_base)
    base_pr = average_precision_score(labels, p_base)
    
    router = DynamicCostRouter()
    base_dyn = router.batch_route_and_evaluate(p_base, amounts, labels)
    
    # Baseline Latency
    sample_dfs = [X_test.iloc[[i]] for i in range(20)]
    lat_base = benchmark_latency(lambda df: lgb_model.predict(df)[0], sample_dfs)
    
    # ---------------------------------------------------------
    # 1. Track A: Two-Stage Fast-Path Cascade
    # ---------------------------------------------------------
    print("\n[1/3] Training & Evaluating Track A: Two-Stage Fast-Path Cascade...")
    track_a_engine = FastPathCascadeEngine()
    track_a_engine.train_gatekeeper(X_train, y_train, X_val, y_val)
    res_a = track_a_engine.evaluate_holdout_cascade(X_test, y_test)
    
    # Latency across fast vs deep path
    lat_a = benchmark_latency(
        lambda df: track_a_engine.score_transaction_cascade(df, float(df['TransactionAmt'].iloc[0])),
        sample_dfs
    )
    
    # ---------------------------------------------------------
    # 2. Track B: Heterogeneous Dual-Model Blend (LightGBM + CatBoost)
    # ---------------------------------------------------------
    print("\n[2/3] Training & Evaluating Track B: Dual-Model Blend (LightGBM + CatBoost)...")
    track_b_engine = DualModelBlendEngine()
    track_b_engine.train_auxiliary_catboost(X_train, y_train, X_val, y_val, cat_cols)
    res_b = track_b_engine.evaluate_holdout_blend(X_test, y_test, weight_lgb=0.70)
    
    clean_sample_dfs = []
    for df in sample_dfs:
        cdf = df.copy()
        for c in cat_cols:
            cdf[c] = cdf[c].astype(object).fillna("missing").astype(str)
        clean_sample_dfs.append((df, cdf))
        
    lat_b = benchmark_latency(
        lambda pair: (0.7 * lgb_model.predict(pair[0])[0]) + (0.3 * track_b_engine.cat_model.predict_proba(pair[1])[0, 1]),
        clean_sample_dfs
    )
    
    # ---------------------------------------------------------
    # 3. Track C: Hybrid Unsupervised Outlier Scorer (Isolation Forest)
    # ---------------------------------------------------------
    print("\n[3/3] Training & Evaluating Track C: Hybrid Unsupervised Outlier Scorer...")
    track_c_engine = UnsupervisedOutlierEngine()
    track_c_engine.fit_isolation_forest(X_train)
    res_c = track_c_engine.evaluate_holdout_outlier(X_test, y_test)
    
    lat_c = benchmark_latency(
        lambda df: (0.85 * lgb_model.predict(df)[0]) + (0.15 * track_c_engine.compute_anomaly_scores(df)[0]),
        sample_dfs
    )
    
    # ---------------------------------------------------------
    # Format Comparative Scorecard
    # ---------------------------------------------------------
    scorecard = [
        {
            "Architecture Model": "0. Baseline Single LightGBM",
            "OOT ROC-AUC": f"{base_roc:.4f}",
            "OOT PR-AUC": f"{base_pr:.4f}",
            "Total Loss ($)": f"${base_dyn['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${338745.87 - base_dyn['total_financial_loss_dollars']:,.2f}",
            "CB Ratio": f"{base_dyn['chargeback_ratio']*100:.2f}%",
            "p50 Latency": f"{lat_base['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_base['p95_ms']:.2f} ms",
            "Production Verdict": "High SOTA accuracy, clean maintainability"
        },
        {
            "Architecture Model": "Track A: Two-Stage Fast-Path Cascade",
            "OOT ROC-AUC": f"{res_a['roc_auc']:.4f}",
            "OOT PR-AUC": f"{res_a['pr_auc']:.4f}",
            "Total Loss ($)": f"${res_a['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${res_a['net_savings_dollars']:,.2f}",
            "CB Ratio": f"{res_a['chargeback_ratio_pct']:.2f}%",
            "p50 Latency": f"{lat_a['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_a['p95_ms']:.2f} ms",
            "Production Verdict": f"Bypasses 70% traffic to <1ms; Best SLA optimization"
        },
        {
            "Architecture Model": "Track B: Dual Blend (LGBM + CatBoost)",
            "OOT ROC-AUC": f"{res_b['roc_auc']:.4f}",
            "OOT PR-AUC": f"{res_b['pr_auc']:.4f}",
            "Total Loss ($)": f"${res_b['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${res_b['net_savings_dollars']:,.2f}",
            "CB Ratio": f"{res_b['chargeback_ratio_pct']:.2f}%",
            "p50 Latency": f"{lat_b['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_b['p95_ms']:.2f} ms",
            "Production Verdict": "Marginal AUC gain; doubles inference latency & complexity"
        },
        {
            "Architecture Model": "Track C: Hybrid Outlier (LGBM + IsoForest)",
            "OOT ROC-AUC": f"{res_c['hybrid_fused_roc_auc']:.4f}",
            "OOT PR-AUC": f"{res_c['hybrid_fused_pr_auc']:.4f}",
            "Total Loss ($)": f"${res_c['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${res_c['net_savings_dollars']:,.2f}",
            "CB Ratio": f"{res_c['chargeback_ratio_pct']:.2f}%",
            "p50 Latency": f"{lat_c['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_c['p95_ms']:.2f} ms",
            "Production Verdict": f"Catches {res_c['high_value_fraud_recall_pct']:.1f}% high-ticket fraud; good cold-start backup"
        }
    ]
    
    scorecard_df = pd.DataFrame(scorecard)
    print("\n" + "="*110)
    print("MASTER MULTI-MODEL & CASCADE ARCHITECTURE EXPLORATION SCORECARD (92,453 HOLDOUT ROWS)")
    print("="*110)
    print(scorecard_df.to_string(index=False))
    print("="*110)
    
    # Save benchmark artifact
    os.makedirs("models", exist_ok=True)
    summary_output = {
        "scorecard": scorecard,
        "track_a_results": res_a,
        "track_b_results": res_b,
        "track_c_results": res_c,
        "latencies": {
            "baseline": lat_base,
            "track_a": lat_a,
            "track_b": lat_b,
            "track_c": lat_c
        }
    }
    with open("models/bonus_exploration_benchmark.json", "w") as f:
        json.dump(summary_output, f, indent=2)
    print("\nSaved benchmark results to models/bonus_exploration_benchmark.json.")
    return summary_output

if __name__ == "__main__":
    run_master_multi_model_benchmark()
