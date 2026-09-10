import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import time
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter, CostMatrixConfig

def evaluate_predictions_on_router(probs: np.ndarray, amounts: np.ndarray, labels: np.ndarray, router: DynamicCostRouter):
    """
    Vectorized statistical and financial evaluation of predicted probabilities on the holdout test set.
    """
    # 1. Statistical calibration & discrimination metrics
    roc = roc_auc_score(labels, probs)
    pr = average_precision_score(labels, probs)
    brier = brier_score_loss(labels, probs)
    # Clip slightly for log loss stability
    eps = 1e-15
    clipped_probs = np.clip(probs, eps, 1.0 - eps)
    lloss = log_loss(labels, clipped_probs)
    
    # 2. Dynamic Cost Router Financial evaluation
    dyn_results = router.batch_route_and_evaluate(probs, amounts, labels)
    total_dollar_loss = dyn_results["total_financial_loss_dollars"]
    chargeback_ratio = dyn_results["chargeback_ratio"]
    approved_count = dyn_results["approve_count"]
    step_up_count = dyn_results["step_up_count"]
    decline_count = dyn_results["decline_count"]
    loss_approve_fraud = dyn_results["loss_approve_fraud"]
    loss_decline_legit = dyn_results["loss_decline_legit"]
    loss_step_up_total = dyn_results["loss_step_up_total"]
    
    # Static 0.50 reference baseline
    is_declined_50 = (probs >= 0.50)
    is_approved_50 = ~is_declined_50
    loss_fn_50 = np.sum(amounts[is_approved_50 & (labels == 1)] + router.cfg.chargeback_fee)
    loss_fp_50 = np.sum((amounts[is_declined_50 & (labels == 0)] * router.cfg.interchange_margin) + router.cfg.customer_friction_cost)
    static_50_loss = float(loss_fn_50 + loss_fp_50)
    net_saved_vs_static_50 = static_50_loss - total_dollar_loss
    
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
        mask = (amounts >= low) & (amounts < high)
        if np.any(mask):
            tier_res = router.batch_route_and_evaluate(probs[mask], amounts[mask], labels[mask])
            tier_losses[name] = tier_res["total_financial_loss_dollars"]
        else:
            tier_losses[name] = 0.0
            
    return {
        "roc_auc": roc,
        "pr_auc": pr,
        "brier_score": brier,
        "log_loss": lloss,
        "mean_prob": float(np.mean(probs)),
        "p50_prob": float(np.median(probs)),
        "p95_prob": float(np.percentile(probs, 95)),
        "p99_prob": float(np.percentile(probs, 99)),
        "total_dollar_loss": total_dollar_loss,
        "loss_approve_fraud": loss_approve_fraud,
        "loss_decline_legit": loss_decline_legit,
        "loss_step_up_total": loss_step_up_total,
        "static_50_loss": static_50_loss,
        "net_saved_vs_static_50": net_saved_vs_static_50,
        "chargeback_ratio": chargeback_ratio,
        "approved_count": approved_count,
        "step_up_count": step_up_count,
        "decline_count": decline_count,
        "tier_losses": tier_losses
    }

def run_calibration_experiment():
    print("=" * 85)
    print("LEVER 2 EXPERIMENT: POST-HOC PROBABILITY CALIBRATION BENCHMARK")
    print("=" * 85)
    
    # 1. Load dataset partitions
    print("\n[1/5] Loading 3-way temporal dataset partitions...")
    X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols = get_temporal_splits()
    print(f"Loaded: Train={len(X_train):,} rows, Val={len(X_val):,} rows, Test={len(X_test):,} rows.")
    
    val_labels = y_val.values
    test_labels = y_test.values
    test_amounts = X_test['TransactionAmt'].values
    
    print(f"Empirical Fraud Rate: Val={np.mean(val_labels)*100:.2f}%, Test={np.mean(test_labels)*100:.2f}%")
    
    # 2. Load production baseline model
    print("\n[2/5] Loading production booster (models/fraud_lgb_model.txt)...")
    base_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    
    # Generate raw validation and test predictions
    print("Generating raw model predictions on Val (Month 5) and Test (Month 6)...")
    val_raw_probs = base_model.predict(X_val)
    test_raw_probs = base_model.predict(X_test)
    
    print(f"Raw Probabilities: Val Mean={np.mean(val_raw_probs)*100:.2f}%, Test Mean={np.mean(test_raw_probs)*100:.2f}%")
    print(f"(Notice: Actual fraud prevalence is ~3.7%, but raw model predicts ~{np.mean(test_raw_probs)*100:.1f}% due to scale_pos_weight=6.77)")
    
    # 3. Fit Calibrators on Month 5 Validation Split (Disjoint from Test)
    print("\n[3/5] Fitting candidate probability calibrators on Month 5 validation split...")
    
    # Method 1: Bayes Odds Inversion (Analytical)
    # Using scale_pos_weight = 6.77022
    with open("models/best_params.json", "r") as f:
        best_params = json.load(f)
    w = float(best_params.get("scale_pos_weight", 6.77022))
    
    def invert_odds(p, weight):
        # p_true = p / (p + w * (1 - p))
        eps = 1e-12
        p_safe = np.clip(p, eps, 1.0 - eps)
        return p_safe / (p_safe + weight * (1.0 - p_safe))
        
    t0 = time.perf_counter()
    test_bayes_probs = invert_odds(test_raw_probs, w)
    bayes_latency_us = (time.perf_counter() - t0) * 1e6 / len(test_raw_probs)
    
    # Method 2: Isotonic Regression
    print("  -> Fitting Isotonic Regression (out_of_bounds='clip')...")
    t0 = time.perf_counter()
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(val_raw_probs, val_labels)
    t_iso_fit = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    test_iso_probs = iso.predict(test_raw_probs)
    iso_latency_us = (time.perf_counter() - t0) * 1e6 / len(test_raw_probs)
    print(f"     Fitted in {t_iso_fit:.3f}s. Batch inference latency: {iso_latency_us:.2f} us/sample.")
    
    # Method 3: Platt Scaling (Logistic Regression on Raw Log-Odds / Margin)
    print("  -> Fitting Platt Scaling (Logistic Regression)...")
    val_logits = logit(np.clip(val_raw_probs, 1e-12, 1.0 - 1e-12)).reshape(-1, 1)
    test_logits = logit(np.clip(test_raw_probs, 1e-12, 1.0 - 1e-12)).reshape(-1, 1)
    
    t0 = time.perf_counter()
    platt = LogisticRegression(solver="lbfgs", max_iter=1000)
    platt.fit(val_logits, val_labels)
    t_platt_fit = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    test_platt_probs = platt.predict_proba(test_logits)[:, 1]
    platt_latency_us = (time.perf_counter() - t0) * 1e6 / len(test_raw_probs)
    print(f"     Fitted in {t_platt_fit:.3f}s (Intercept: {platt.intercept_[0]:.4f}, Slope: {platt.coef_[0][0]:.4f}). Latency: {platt_latency_us:.2f} us/sample.")
    
    # Method 4: Temperature Scaling (Minimizing Validation NLL)
    print("  -> Fitting Temperature Scaling...")
    t0 = time.perf_counter()
    def nll_obj(T):
        scaled_logits = val_logits.flatten() / T
        scaled_probs = expit(scaled_logits)
        eps = 1e-15
        p_c = np.clip(scaled_probs, eps, 1.0 - eps)
        return -np.mean(val_labels * np.log(p_c) + (1 - val_labels) * np.log(1 - p_c))
        
    res = minimize_scalar(nll_obj, bounds=(0.1, 10.0), method='bounded')
    opt_T = float(res.x)
    t_temp_fit = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    test_temp_probs = expit(test_logits.flatten() / opt_T)
    temp_latency_us = (time.perf_counter() - t0) * 1e6 / len(test_raw_probs)
    print(f"     Optimized T={opt_T:.4f} in {t_temp_fit:.3f}s. Latency: {temp_latency_us:.2f} us/sample.")
    
    # 4. Evaluate all methods through the Dynamic Cost Router
    print("\n[4/5] Evaluating all calibration methods through DynamicCostRouter...")
    router = DynamicCostRouter()
    
    candidates = {
        "Uncalibrated Baseline (Raw Booster)": (test_raw_probs, 0.0),
        "Bayes Odds Inversion (w=6.77)": (test_bayes_probs, bayes_latency_us),
        "Isotonic Calibration (Non-Parametric)": (test_iso_probs, iso_latency_us),
        "Platt Scaling (Sigmoid Logit Fit)": (test_platt_probs, platt_latency_us),
        "Temperature Scaling (T-Scaled Logit)": (test_temp_probs, temp_latency_us),
    }
    
    results = {}
    for name, (probs, lat_us) in candidates.items():
        metrics = evaluate_predictions_on_router(probs, test_amounts, test_labels, router)
        metrics["latency_us"] = lat_us
        results[name] = metrics
        
    baseline_loss = results["Uncalibrated Baseline (Raw Booster)"]["total_dollar_loss"]
    
    # 5. Comparative Scorecard
    print("\n[5/5] Comparative Calibration Scorecard on 92,453 Holdout Transactions:")
    print("=" * 115)
    
    rows = []
    for name, m in results.items():
        delta_vs_baseline = baseline_loss - m["total_dollar_loss"]
        delta_str = f"+${delta_vs_baseline:,.2f}" if delta_vs_baseline > 0 else (f"-${abs(delta_vs_baseline):,.2f}" if delta_vs_baseline < 0 else "$0.00 (Ref)")
        rows.append({
            "Calibration Method": name,
            "Brier (min)": f"{m['brier_score']:.4f}",
            "Log-Loss (min)": f"{m['log_loss']:.4f}",
            "PR-AUC": f"{m['pr_auc']:.4f}",
            "Mean P(%)": f"{m['mean_prob']*100:.2f}%",
            "Total Loss ($)": f"${m['total_dollar_loss']:,.2f}",
            "Net Savings Uplift": delta_str,
            "Chargeback %": f"{m['chargeback_ratio']*100:.2f}%",
            "Approve": f"{m['approved_count']:,}",
            "3DS Step-Up": f"{m['step_up_count']:,}",
            "Decline": f"{m['decline_count']:,}",
            "Latency": f"{m['latency_us']:.2f} us"
        })
        
    df_scorecard = pd.DataFrame(rows)
    print(df_scorecard.to_string(index=False))
    print("=" * 115)
    
    # Detailed Cost Component Breakdown
    print("\nLoss Decomposition by Category ($):")
    comp_rows = []
    for name, m in results.items():
        comp_rows.append({
            "Method": name,
            "Fraud Leakage (Approve)": f"${m['loss_approve_fraud']:,.2f}",
            "False Decline (Legit)": f"${m['loss_decline_legit']:,.2f}",
            "3DS Friction & Fees": f"${m['loss_step_up_total']:,.2f}",
            "Total Financial Loss": f"${m['total_dollar_loss']:,.2f}"
        })
    print(pd.DataFrame(comp_rows).to_string(index=False))
    print("=" * 115)
    
    # Spend Tier Breakdown
    print("\nDetailed Spend Tier Financial Loss Comparison ($):")
    tier_names = list(results["Uncalibrated Baseline (Raw Booster)"]["tier_losses"].keys())
    tier_rows = []
    for tier in tier_names:
        row = {"Spend Tier": tier}
        for name, m in results.items():
            row[name] = f"${m['tier_losses'][tier]:,.2f}"
        tier_rows.append(row)
    print(pd.DataFrame(tier_rows).to_string(index=False))
    print("=" * 115)
    
    # 6. What if Cost Router thresholds are adapted for Calibrated Probabilities?
    print("\n[6/6] Adapting Dynamic Cost Router Thresholds for Calibrated Models (Tuned on Val Set)...")
    
    # Generate validation predictions for each method
    val_bayes_probs = invert_odds(val_raw_probs, w)
    val_iso_probs = iso.predict(val_raw_probs)
    val_platt_probs = platt.predict_proba(val_logits)[:, 1]
    val_temp_probs = expit(val_logits.flatten() / opt_T)
    val_amounts = X_val['TransactionAmt'].values
    
    # We test scaling tau_step_up by factor alpha in [0.1, 0.2, ..., 1.5] on Val set
    cal_methods = {
        "Isotonic Calibration": (val_iso_probs, test_iso_probs),
        "Platt Scaling": (val_platt_probs, test_platt_probs),
        "Temperature Scaling": (val_temp_probs, test_temp_probs)
    }
    
    adapted_results = []
    for m_name, (v_p, t_p) in cal_methods.items():
        best_alpha = 1.0
        min_val_loss = float('inf')
        
        # Grid search over threshold scaling factor alpha on Month 5 Validation
        for alpha in np.linspace(0.1, 1.2, 23):
            cfg = CostMatrixConfig(
                min_step_up_threshold=max(0.005, 0.03 * alpha),
                max_step_up_threshold=max(0.05, 0.25 * alpha),
                min_decline_threshold=max(0.10, 0.35 * alpha),
                max_decline_threshold=max(0.20, 0.80 * alpha)
            )
            r_temp = DynamicCostRouter(config=cfg)
            res_val = r_temp.batch_route_and_evaluate(v_p * (1.0 / alpha), val_amounts, val_labels)
            if res_val["total_financial_loss_dollars"] < min_val_loss:
                min_val_loss = res_val["total_financial_loss_dollars"]
                best_alpha = alpha
                
        # Now evaluate the optimal configuration on the Holdout Test Set
        cfg_opt = CostMatrixConfig(
            min_step_up_threshold=max(0.005, 0.03 * best_alpha),
            max_step_up_threshold=max(0.05, 0.25 * best_alpha),
            min_decline_threshold=max(0.10, 0.35 * best_alpha),
            max_decline_threshold=max(0.20, 0.80 * best_alpha)
        )
        r_opt = DynamicCostRouter(config=cfg_opt)
        opt_test_res = r_opt.batch_route_and_evaluate(t_p * (1.0 / best_alpha), test_amounts, test_labels)
        
        loss_val = opt_test_res["total_financial_loss_dollars"]
        gain_vs_base = baseline_loss - loss_val
        gain_str = f"+${gain_vs_base:,.2f}" if gain_vs_base > 0 else f"-${abs(gain_vs_base):,.2f}"
        
        adapted_results.append({
            "Method + Tuned Threshold": f"{m_name} (alpha={best_alpha:.2f})",
            "Holdout Total Loss ($)": f"${loss_val:,.2f}",
            "Delta vs Baseline": gain_str,
            "Chargeback %": f"{opt_test_res['chargeback_ratio']*100:.2f}%",
            "Approve": f"{opt_test_res['approve_count']:,}",
            "3DS Step-Up": f"{opt_test_res['step_up_count']:,}",
            "Decline": f"{opt_test_res['decline_count']:,}"
        })
        
    print(pd.DataFrame(adapted_results).to_string(index=False))
    print("=" * 115)

    return results, iso, platt

if __name__ == "__main__":
    run_calibration_experiment()

