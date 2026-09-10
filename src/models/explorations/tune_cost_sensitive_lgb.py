import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import time
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter, CostMatrixConfig

def calculate_weights(amounts: np.ndarray, labels: np.ndarray, method: str, base_pos_weight: float = 6.77) -> np.ndarray:
    """
    Computes example-dependent cost-sensitive sample weights for LightGBM training.
    """
    weights = np.ones_like(amounts, dtype=np.float32)
    y_fraud = (labels == 1)
    
    if method == "baseline_unweighted":
        # Handled by scale_pos_weight in LightGBM params
        return weights
        
    elif method == "log_monetary":
        # w_i = base * (1 + 0.5 * log10(1 + Amount))
        # $10 fraud -> weight 10.15
        # $100 fraud -> weight 13.54
        # $1000 fraud -> weight 16.92
        fraud_weights = base_pos_weight * (1.0 + 0.5 * np.log10(1.0 + np.maximum(0.0, amounts[y_fraud])))
        weights[y_fraud] = fraud_weights.astype(np.float32)
        return weights
        
    elif method == "exposure_sqrt":
        # Relative exposure: (Amt + 25) / (MeanAmt + 25), compressed via square-root
        mean_amt = 135.0
        exposure_ratio = (amounts[y_fraud] + 25.0) / (mean_amt + 25.0)
        fraud_weights = base_pos_weight * np.sqrt(np.maximum(0.1, exposure_ratio))
        weights[y_fraud] = np.clip(fraud_weights, base_pos_weight * 0.5, base_pos_weight * 4.0).astype(np.float32)
        return weights
        
    elif method == "bounded_asymmetric":
        # Bounded logarithmic loss scaling capped at 3x base
        fraud_weights = base_pos_weight * (1.0 + np.log(1.0 + np.maximum(0.0, amounts[y_fraud]) / 50.0))
        weights[y_fraud] = np.clip(fraud_weights, base_pos_weight, base_pos_weight * 3.0).astype(np.float32)
        return weights
        
    else:
        raise ValueError(f"Unknown weighting method: {method}")

def evaluate_model_on_cost_router(model, X_test, y_test, router: DynamicCostRouter):
    """
    Evaluates a trained model on the holdout test set using both statistical and financial metrics.
    """
    test_amounts = X_test['TransactionAmt'].values
    test_labels = y_test.values
    
    # 1. Inference probabilities
    t0 = time.perf_counter()
    probs = model.predict(X_test)
    inf_latency_ms = (time.perf_counter() - t0) * 1000.0 / len(probs)
    
    # 2. Statistical metrics
    roc = roc_auc_score(test_labels, probs)
    pr = average_precision_score(test_labels, probs)
    brier = brier_score_loss(test_labels, probs)
    loss = log_loss(test_labels, probs)
    
    # 3. Dynamic Cost Router Financial evaluation
    dyn_results = router.batch_route_and_evaluate(probs, test_amounts, test_labels)
    total_dollar_loss = dyn_results["total_financial_loss_dollars"]
    chargeback_ratio = dyn_results["chargeback_ratio"]
    approved_count = dyn_results["approve_count"]
    step_up_count = dyn_results["step_up_count"]
    decline_count = dyn_results["decline_count"]
    
    # Static 0.50 comparison baseline
    is_declined_50 = (probs >= 0.50)
    is_approved_50 = ~is_declined_50
    loss_fn_50 = np.sum(test_amounts[is_approved_50 & (test_labels == 1)] + router.cfg.chargeback_fee)
    loss_fp_50 = np.sum((test_amounts[is_declined_50 & (test_labels == 0)] * router.cfg.interchange_margin) + router.cfg.customer_friction_cost)
    static_50_loss = float(loss_fn_50 + loss_fp_50)
    
    net_saved_vs_static_50 = static_50_loss - total_dollar_loss
    roi_vs_static_50 = (net_saved_vs_static_50 / static_50_loss) * 100.0
    
    # Spend tier breakdown
    tiers = [
        ("Micro ($0-$25)", 0.0, 25.0),
        ("Low ($25-$100)", 25.0, 100.0),
        ("Mid ($100-$500)", 100.0, 500.0),
        ("High ($500-$2000)", 500.0, 2000.0),
        ("Ultra-High ($2000+)", 2000.0, float('inf'))
    ]
    tier_losses = {}
    for name, low, high in tiers:
        mask = (test_amounts >= low) & (test_amounts < high)
        if np.any(mask):
            tier_res = router.batch_route_and_evaluate(probs[mask], test_amounts[mask], test_labels[mask])
            tier_losses[name] = tier_res["total_financial_loss_dollars"]
        else:
            tier_losses[name] = 0.0
            
    return {
        "roc_auc": roc,
        "pr_auc": pr,
        "brier_score": brier,
        "log_loss": loss,
        "total_dollar_loss": total_dollar_loss,
        "static_50_loss": static_50_loss,
        "net_saved_vs_static_50": net_saved_vs_static_50,
        "roi_vs_static_50": roi_vs_static_50,
        "chargeback_ratio": chargeback_ratio,
        "approved_count": approved_count,
        "step_up_count": step_up_count,
        "decline_count": decline_count,
        "tier_losses": tier_losses,
        "avg_inf_latency_ms": inf_latency_ms
    }

def run_cost_sensitive_experiment():
    print("="*80)
    print("LEVER 1 EXPERIMENT: COST-SENSITIVE VALUE-AWARE SAMPLE WEIGHTING")
    print("="*80)
    
    # Load dataset
    print("\n[1/4] Loading 3-way temporal dataset partitions...")
    X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols = get_temporal_splits()
    print(f"Loaded: Train={len(X_train):,} rows, Val={len(X_val):,} rows, Test={len(X_test):,} rows.")
    
    # Load best params
    with open("models/best_params.json", "r") as f:
        best_params = json.load(f)
    base_pos_weight = float(best_params.get("scale_pos_weight", 6.77))
    
    router = DynamicCostRouter()
    
    # Evaluate current baseline production model
    print("\n[2/4] Evaluating current production baseline booster (models/fraud_lgb_model.txt)...")
    base_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    baseline_metrics = evaluate_model_on_cost_router(base_model, X_test, y_test, router)
    
    # Candidate methods
    candidates = [
        ("log_monetary", "Variant 1: Log-Scaled Monetary Weighting"),
        ("exposure_sqrt", "Variant 2: Exposure Square-Root Weighting"),
        ("bounded_asymmetric", "Variant 3: Bounded Asymmetric Loss Weighting")
    ]
    
    results = {
        "Production Baseline (scale_pos_weight=6.77)": baseline_metrics
    }
    
    train_amounts = X_train['TransactionAmt'].values
    train_labels = y_train.values
    
    models = {}
    
    print("\n[3/4] Training candidate cost-sensitive LightGBM models on 410k transactions...")
    for method_id, method_desc in candidates:
        print(f"\n--- Training {method_desc} ---")
        weights = calculate_weights(train_amounts, train_labels, method=method_id, base_pos_weight=base_pos_weight)
        
        # In cost-sensitive weighting, we pass sample_weight and set scale_pos_weight=1.0 to avoid double-weighting
        params = {
            'objective': 'binary',
            'metric': ['auc', 'average_precision'],
            'boosting_type': 'gbdt',
            'verbosity': -1,
            'n_jobs': -1,
            'seed': 42,
            **best_params,
            'scale_pos_weight': 1.0  # Weighting is now handled directly via sample_weight
        }
        
        dtrain = lgb.Dataset(X_train, label=y_train, weight=weights)
        dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
        
        t_train_start = time.perf_counter()
        candidate_model = lgb.train(
            params,
            dtrain,
            num_boost_round=250,
            valid_sets=[dtrain, dval],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
        )
        t_train = time.perf_counter() - t_train_start
        print(f"Training completed in {t_train:.1f}s (Best iteration: {candidate_model.best_iteration})")
        
        cand_metrics = evaluate_model_on_cost_router(candidate_model, X_test, y_test, router)
        results[method_desc] = cand_metrics
        models[method_id] = candidate_model
        
    print("\n[4/4] Master Evaluation & Comparative Scorecard on 92,453 Holdout Transactions:")
    print("="*105)
    
    scorecard_rows = []
    for name, m in results.items():
        scorecard_rows.append({
            "Model Variant": name,
            "ROC-AUC": f"{m['roc_auc']:.4f}",
            "PR-AUC": f"{m['pr_auc']:.4f}",
            "Brier Score": f"{m['brier_score']:.4f}",
            "Total Dollar Loss ($)": f"${m['total_dollar_loss']:,.2f}",
            "Net Saved vs Static 0.50": f"+${m['net_saved_vs_static_50']:,.2f}",
            "Savings Uplift vs Baseline": f"+${(baseline_metrics['total_dollar_loss'] - m['total_dollar_loss']):,.2f}" if name != "Production Baseline (scale_pos_weight=6.77)" else "$0.00 (Ref)",
            "Chargeback %": f"{m['chargeback_ratio']*100:.2f}%",
            "Approved": f"{m['approved_count']:,}",
            "3DS Step-Up": f"{m['step_up_count']:,}",
            "Declined": f"{m['decline_count']:,}"
        })
        
    scorecard_df = pd.DataFrame(scorecard_rows)
    print(scorecard_df.to_string(index=False))
    print("="*105)
    
    # Spend Tier Detailed Breakdown
    print("\nDetailed Spend Tier Loss Comparison ($):")
    tier_names = list(baseline_metrics["tier_losses"].keys())
    tier_rows = []
    for tier in tier_names:
        row = {"Spend Tier": tier}
        for model_name, m in results.items():
            row[model_name] = f"${m['tier_losses'][tier]:,.2f}"
        tier_rows.append(row)
    print(pd.DataFrame(tier_rows).to_string(index=False))
    print("="*105)
    
    # Check for best model
    best_variant = min(results.keys(), key=lambda k: results[k]["total_dollar_loss"])
    best_saved = baseline_metrics['total_dollar_loss'] - results[best_variant]['total_dollar_loss']
    print(f"\nWinning Model: {best_variant}")
    print(f"Total Loss: ${results[best_variant]['total_dollar_loss']:,.2f}")
    if best_saved > 0:
        print(f"Additional Dollar Savings over Production Baseline: +${best_saved:,.2f}!")
    else:
        print("Production baseline remains ahead.")

if __name__ == "__main__":
    run_cost_sensitive_experiment()
