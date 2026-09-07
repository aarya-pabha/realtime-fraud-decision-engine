import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import time
import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
from optuna.samplers import TPESampler

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter, CostMatrixConfig

optuna.logging.set_verbosity(optuna.logging.WARNING)

def evaluate_tier_policy(
    probs: np.ndarray,
    amounts: np.ndarray,
    labels: np.ndarray,
    step_up_scale: float,
    decline_multiplier: float,
    min_step_up: float,
    max_step_up: float,
    min_decline: float,
    max_decline: float,
    cfg: CostMatrixConfig = None
):
    """
    Vectorized evaluation of routing policy on a subset of transactions in sub-millisecond C/NumPy speed.
    """
    if len(probs) == 0:
        return {
            "total_dollar_loss": 0.0,
            "loss_approve_fraud": 0.0,
            "loss_decline_legit": 0.0,
            "loss_step_up_total": 0.0,
            "chargeback_count": 0,
            "chargeback_ratio": 0.0,
            "approve_count": 0,
            "step_up_count": 0,
            "decline_count": 0
        }
        
    cfg = cfg or CostMatrixConfig()
    c_fn = amounts + cfg.chargeback_fee
    c_fp = (amounts * cfg.interchange_margin) + cfg.customer_friction_cost
    tau_star = c_fp / (c_fn + c_fp)
    
    tau_step_up = np.clip(tau_star * step_up_scale, min_step_up, max_step_up)
    tau_decline = np.clip(tau_star * decline_multiplier, min_decline, max_decline)
    tau_decline = np.maximum(tau_decline, tau_step_up + 0.01)
    
    is_approve = probs < tau_step_up
    is_step_up = (probs >= tau_step_up) & (probs < tau_decline)
    is_decline = probs >= tau_decline
    
    y_fraud = (labels == 1)
    y_legit = (labels == 0)
    
    loss_approve_fraud = np.sum(amounts[is_approve & y_fraud] + cfg.chargeback_fee)
    loss_decline_legit = np.sum((amounts[is_decline & y_legit] * cfg.interchange_margin) + cfg.customer_friction_cost)
    
    p_bypass = 1.0 - cfg.step_up_fraud_block_rate
    p_abandon = 1.0 - cfg.step_up_legit_success_rate
    n_step_up = np.sum(is_step_up)
    cost_3ds_auth = n_step_up * cfg.auth_3ds_cost
    
    loss_3ds_fraud = np.sum(p_bypass * (amounts[is_step_up & y_fraud] + cfg.chargeback_fee))
    loss_3ds_legit = np.sum(p_abandon * ((amounts[is_step_up & y_legit] * cfg.interchange_margin) + cfg.customer_friction_cost))
    
    total_dollar_loss = float(
        loss_approve_fraud + loss_decline_legit +
        cost_3ds_auth + loss_3ds_fraud + loss_3ds_legit
    )
    
    total_chargebacks = int(np.sum(is_approve & y_fraud) + np.sum(is_step_up & y_fraud) * p_bypass)
    chargeback_ratio = float(total_chargebacks / len(probs)) if len(probs) > 0 else 0.0
    
    return {
        "total_dollar_loss": total_dollar_loss,
        "loss_approve_fraud": float(loss_approve_fraud),
        "loss_decline_legit": float(loss_decline_legit),
        "loss_step_up_total": float(cost_3ds_auth + loss_3ds_fraud + loss_3ds_legit),
        "chargeback_count": total_chargebacks,
        "chargeback_ratio": chargeback_ratio,
        "approve_count": int(np.sum(is_approve)),
        "step_up_count": int(n_step_up),
        "decline_count": int(np.sum(is_decline))
    }

def optimize_tier(
    tier_name: str,
    v_probs: np.ndarray,
    v_amounts: np.ndarray,
    v_labels: np.ndarray,
    n_trials: int = 200,
    seed: int = 42
):
    """
    Optimizes routing hyperparameters for a specific spend tier on Month 5 Validation.
    """
    print(f"\n--- Optimizing {tier_name} ({len(v_probs):,} validation transactions) ---")
    cfg_prod = CostMatrixConfig()
    
    # Baseline for this tier
    base_tier_res = evaluate_tier_policy(
        v_probs, v_amounts, v_labels,
        step_up_scale=1.0, decline_multiplier=4.0,
        min_step_up=0.03, max_step_up=0.25,
        min_decline=0.35, max_decline=0.80,
        cfg=cfg_prod
    )
    print(f"  Baseline Tier Loss: ${base_tier_res['total_dollar_loss']:,.2f} (CB Ratio: {base_tier_res['chargeback_ratio']*100:.2f}%)")
    
    def objective(trial):
        step_up_scale = trial.suggest_float("step_up_scale", 0.30, 2.50, step=0.05)
        decline_multiplier = trial.suggest_float("decline_multiplier", 1.50, 10.00, step=0.25)
        min_step_up = trial.suggest_float("min_step_up", 0.005, 0.100, step=0.005)
        max_step_up = trial.suggest_float("max_step_up", 0.08, 0.40, step=0.02)
        min_decline = trial.suggest_float("min_decline", 0.15, 0.75, step=0.02)
        max_decline = trial.suggest_float("max_decline", 0.50, 0.95, step=0.05)
        
        if min_step_up >= max_step_up or min_decline >= max_decline or min_step_up >= min_decline:
            return 1e8
            
        metrics = evaluate_tier_policy(
            v_probs, v_amounts, v_labels,
            step_up_scale=step_up_scale,
            decline_multiplier=decline_multiplier,
            min_step_up=min_step_up,
            max_step_up=max_step_up,
            min_decline=min_decline,
            max_decline=max_decline,
            cfg=cfg_prod
        )
        
        loss = metrics["total_dollar_loss"]
        cb_ratio = metrics["chargeback_ratio"]
        
        # Buffer penalty if chargeback ratio is high
        if cb_ratio > 0.010:
            excess_bps = (cb_ratio - 0.010) * 10000.0
            loss += 25000.0 + excess_bps * 200.0
            
        return loss

    sampler = TPESampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    
    # Enqueue production default
    study.enqueue_trial({
        "step_up_scale": 1.0,
        "decline_multiplier": 4.0,
        "min_step_up": 0.03,
        "max_step_up": 0.25,
        "min_decline": 0.35,
        "max_decline": 0.80
    })
    
    t0 = time.perf_counter()
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    t_el = time.perf_counter() - t0
    
    best_p = study.best_params
    best_loss = study.best_value
    print(f"  Completed in {t_el:.2f}s. Best Loss: ${best_loss:,.2f} (Savings: +${base_tier_res['total_dollar_loss'] - best_loss:,.2f})")
    print(f"  Parameters: beta={best_p['step_up_scale']}, k={best_p['decline_multiplier']}, step_range=[{best_p['min_step_up']}, {best_p['max_step_up']}], dec_range=[{best_p['min_decline']}, {best_p['max_decline']}]")
    
    return best_p

def run_level4_experiment():
    print("=" * 95)
    print("LEVER 4 EXPERIMENT: SPEND-TIER SEGMENTED DYNAMIC POLICY OPTIMIZATION")
    print("=" * 95)
    
    # 1. Load dataset partitions
    print("\n[1/4] Loading 3-way temporal dataset partitions...")
    X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, cat_cols = get_temporal_splits()
    print(f"Loaded: Train={len(X_train):,} rows, Val={len(X_val):,} rows, Test={len(X_test):,} rows.")
    
    val_labels = y_val.values
    val_amounts = X_val['TransactionAmt'].values
    test_labels = y_test.values
    test_amounts = X_test['TransactionAmt'].values
    
    # 2. Precompute model predictions
    print("\n[2/4] Generating predictions from production LightGBM booster...")
    base_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    val_probs = base_model.predict(X_val)
    test_probs = base_model.predict(X_test)
    
    # 3. Define 3 Actionable Spend Tiers
    # Tier 1: Low-Ticket (< $100) - High frequency everyday eCommerce & bot testing
    # Tier 2: Mid-Ticket ($100 - $500) - Core consumer purchases
    # Tier 3: High-Ticket (>= $500) - High exposure ATO, electronics, luxury
    tier_definitions = [
        ("Tier 1: Low-Spend (<$100)", 0.0, 100.0),
        ("Tier 2: Mid-Spend ($100-$500)", 100.0, 500.0),
        ("Tier 3: High-Spend ($500+)", 500.0, float('inf'))
    ]
    
    # 4. Optimize each spend tier independently on Month 5 Validation
    print("\n[3/4] Optimizing each spend tier independently on Month 5 Validation...")
    optimized_tier_params = {}
    
    for t_name, low, high in tier_definitions:
        v_mask = (val_amounts >= low) & (val_amounts < high)
        best_p = optimize_tier(
            t_name,
            val_probs[v_mask],
            val_amounts[v_mask],
            val_labels[v_mask],
            n_trials=250,
            seed=42
        )
        optimized_tier_params[t_name] = best_p
        
    # Level 3 Winning Global Parameters (for reference)
    lvl3_global_params = {
        "step_up_scale": 0.85,
        "decline_multiplier": 7.25,
        "min_step_up": 0.015,
        "max_step_up": 0.10,
        "min_decline": 0.59,
        "max_decline": 0.85
    }
    
    # 5. Out-of-Time Benchmark on 92,453 Holdout Transactions
    print("\n[4/4] Out-of-Time Generalization Benchmark on Month 6 Holdout Test Set (92,453 rows)...")
    
    # Strategy 1: Production Default (Reference)
    cfg_prod = CostMatrixConfig()
    strat1_res = evaluate_tier_policy(
        test_probs, test_amounts, test_labels,
        step_up_scale=1.0, decline_multiplier=4.0,
        min_step_up=0.03, max_step_up=0.25,
        min_decline=0.35, max_decline=0.80,
        cfg=cfg_prod
    )
    
    # Strategy 2: Level 3 Global Optuna Policy
    strat2_res = evaluate_tier_policy(
        test_probs, test_amounts, test_labels,
        step_up_scale=lvl3_global_params["step_up_scale"],
        decline_multiplier=lvl3_global_params["decline_multiplier"],
        min_step_up=lvl3_global_params["min_step_up"],
        max_step_up=lvl3_global_params["max_step_up"],
        min_decline=lvl3_global_params["min_decline"],
        max_decline=lvl3_global_params["max_decline"],
        cfg=cfg_prod
    )
    
    # Strategy 3: Level 4 Segmented Tier-Specific Policy
    # We evaluate each tier on test set with its specialized parameters and sum results
    strat3_tier_results = {}
    total_strat3_loss = 0.0
    total_strat3_approve = 0
    total_strat3_step_up = 0
    total_strat3_decline = 0
    total_strat3_cb = 0
    total_strat3_loss_approve_fraud = 0.0
    total_strat3_loss_decline_legit = 0.0
    total_strat3_loss_3ds = 0.0
    
    for t_name, low, high in tier_definitions:
        t_mask = (test_amounts >= low) & (test_amounts < high)
        p_t = optimized_tier_params[t_name]
        t_res = evaluate_tier_policy(
            test_probs[t_mask], test_amounts[t_mask], test_labels[t_mask],
            step_up_scale=p_t["step_up_scale"],
            decline_multiplier=p_t["decline_multiplier"],
            min_step_up=p_t["min_step_up"],
            max_step_up=p_t["max_step_up"],
            min_decline=p_t["min_decline"],
            max_decline=p_t["max_decline"],
            cfg=cfg_prod
        )
        strat3_tier_results[t_name] = t_res
        total_strat3_loss += t_res["total_dollar_loss"]
        total_strat3_approve += t_res["approve_count"]
        total_strat3_step_up += t_res["step_up_count"]
        total_strat3_decline += t_res["decline_count"]
        total_strat3_cb += t_res["chargeback_count"]
        total_strat3_loss_approve_fraud += t_res["loss_approve_fraud"]
        total_strat3_loss_decline_legit += t_res["loss_decline_legit"]
        total_strat3_loss_3ds += t_res["loss_step_up_total"]
        
    strat3_res = {
        "total_dollar_loss": total_strat3_loss,
        "loss_approve_fraud": total_strat3_loss_approve_fraud,
        "loss_decline_legit": total_strat3_loss_decline_legit,
        "loss_step_up_total": total_strat3_loss_3ds,
        "chargeback_count": total_strat3_cb,
        "chargeback_ratio": total_strat3_cb / len(test_probs),
        "approve_count": total_strat3_approve,
        "step_up_count": total_strat3_step_up,
        "decline_count": total_strat3_decline
    }
    
    # Strategy 4: Level 3 + Level 4 Combined Hybrid
    # Tier 1 uses Level 3 global parameters (which achieved lowest loss on <$100),
    # while Tier 2 and Tier 3 use specialized Level 4 parameters.
    hybrid_tier_results = {}
    total_hybrid_loss = 0.0
    total_hybrid_approve = 0
    total_hybrid_step_up = 0
    total_hybrid_decline = 0
    total_hybrid_cb = 0
    total_hybrid_loss_approve_fraud = 0.0
    total_hybrid_loss_decline_legit = 0.0
    total_hybrid_loss_3ds = 0.0
    
    hybrid_params = {
        "Tier 1: Low-Spend (<$100)": lvl3_global_params,
        "Tier 2: Mid-Spend ($100-$500)": optimized_tier_params["Tier 2: Mid-Spend ($100-$500)"],
        "Tier 3: High-Spend ($500+)": optimized_tier_params["Tier 3: High-Spend ($500+)"]
    }
    
    for t_name, low, high in tier_definitions:
        t_mask = (test_amounts >= low) & (test_amounts < high)
        p_t = hybrid_params[t_name]
        h_res = evaluate_tier_policy(
            test_probs[t_mask], test_amounts[t_mask], test_labels[t_mask],
            step_up_scale=p_t["step_up_scale"],
            decline_multiplier=p_t["decline_multiplier"],
            min_step_up=p_t["min_step_up"],
            max_step_up=p_t["max_step_up"],
            min_decline=p_t["min_decline"],
            max_decline=p_t["max_decline"],
            cfg=cfg_prod
        )
        hybrid_tier_results[t_name] = h_res
        total_hybrid_loss += h_res["total_dollar_loss"]
        total_hybrid_approve += h_res["approve_count"]
        total_hybrid_step_up += h_res["step_up_count"]
        total_hybrid_decline += h_res["decline_count"]
        total_hybrid_cb += h_res["chargeback_count"]
        total_hybrid_loss_approve_fraud += h_res["loss_approve_fraud"]
        total_hybrid_loss_decline_legit += h_res["loss_decline_legit"]
        total_hybrid_loss_3ds += h_res["loss_step_up_total"]
        
    strat4_res = {
        "total_dollar_loss": total_hybrid_loss,
        "loss_approve_fraud": total_hybrid_loss_approve_fraud,
        "loss_decline_legit": total_hybrid_loss_decline_legit,
        "loss_step_up_total": total_hybrid_loss_3ds,
        "chargeback_count": total_hybrid_cb,
        "chargeback_ratio": total_hybrid_cb / len(test_probs),
        "approve_count": total_hybrid_approve,
        "step_up_count": total_hybrid_step_up,
        "decline_count": total_hybrid_decline
    }
    
    # Master Scorecard
    print("\n" + "=" * 115)
    print("MASTER COMPARATIVE SCORECARD: BASELINE vs LEVEL 3 vs LEVEL 4 vs COMBINED HYBRID:")
    print("=" * 115)
    
    scorecard_data = [
        {
            "Architecture / Strategy": "Production Default Baseline",
            "Total Realized Loss ($)": f"${strat1_res['total_dollar_loss']:,.2f}",
            "Net Savings vs Base": "$0.00 (Ref)",
            "Chargeback %": f"{strat1_res['chargeback_ratio']*100:.2f}%",
            "Approved": f"{strat1_res['approve_count']:,}",
            "3DS Step-Up": f"{strat1_res['step_up_count']:,}",
            "Declined": f"{strat1_res['decline_count']:,}"
        },
        {
            "Architecture / Strategy": "Level 3: Global Optuna Policy",
            "Total Realized Loss ($)": f"${strat2_res['total_dollar_loss']:,.2f}",
            "Net Savings vs Base": f"+${strat1_res['total_dollar_loss'] - strat2_res['total_dollar_loss']:,.2f}",
            "Chargeback %": f"{strat2_res['chargeback_ratio']*100:.2f}%",
            "Approved": f"{strat2_res['approve_count']:,}",
            "3DS Step-Up": f"{strat2_res['step_up_count']:,}",
            "Declined": f"{strat2_res['decline_count']:,}"
        },
        {
            "Architecture / Strategy": "Level 4: Pure Segmented Policy",
            "Total Realized Loss ($)": f"${strat3_res['total_dollar_loss']:,.2f}",
            "Net Savings vs Base": f"+${strat1_res['total_dollar_loss'] - strat3_res['total_dollar_loss']:,.2f}",
            "Chargeback %": f"{strat3_res['chargeback_ratio']*100:.2f}%",
            "Approved": f"{strat3_res['approve_count']:,}",
            "3DS Step-Up": f"{strat3_res['step_up_count']:,}",
            "Declined": f"{strat3_res['decline_count']:,}"
        },
        {
            "Architecture / Strategy": "Level 3+4: Combined Hybrid Policy",
            "Total Realized Loss ($)": f"${strat4_res['total_dollar_loss']:,.2f}",
            "Net Savings vs Base": f"+${strat1_res['total_dollar_loss'] - strat4_res['total_dollar_loss']:,.2f}",
            "Chargeback %": f"{strat4_res['chargeback_ratio']*100:.2f}%",
            "Approved": f"{strat4_res['approve_count']:,}",
            "3DS Step-Up": f"{strat4_res['step_up_count']:,}",
            "Declined": f"{strat4_res['decline_count']:,}"
        }
    ]
    print(pd.DataFrame(scorecard_data).to_string(index=False))
    print("=" * 115)
    
    # Loss Decomposition
    print("\nLoss Decomposition Comparison ($):")
    decomp_data = [
        {
            "Architecture / Strategy": "Production Default Baseline",
            "Fraud Leakage (Approve)": f"${strat1_res['loss_approve_fraud']:,.2f}",
            "False Decline Friction": f"${strat1_res['loss_decline_legit']:,.2f}",
            "3DS Friction & Fees": f"${strat1_res['loss_step_up_total']:,.2f}",
            "Total Dollar Loss": f"${strat1_res['total_dollar_loss']:,.2f}"
        },
        {
            "Architecture / Strategy": "Level 3: Global Optuna Policy",
            "Fraud Leakage (Approve)": f"${strat2_res['loss_approve_fraud']:,.2f}",
            "False Decline Friction": f"${strat2_res['loss_decline_legit']:,.2f}",
            "3DS Friction & Fees": f"${strat2_res['loss_step_up_total']:,.2f}",
            "Total Dollar Loss": f"${strat2_res['total_dollar_loss']:,.2f}"
        },
        {
            "Architecture / Strategy": "Level 4: Segmented Tier Policy",
            "Fraud Leakage (Approve)": f"${strat3_res['loss_approve_fraud']:,.2f}",
            "False Decline Friction": f"${strat3_res['loss_decline_legit']:,.2f}",
            "3DS Friction & Fees": f"${strat3_res['loss_step_up_total']:,.2f}",
            "Total Dollar Loss": f"${strat3_res['total_dollar_loss']:,.2f}"
        }
    ]
    print(pd.DataFrame(decomp_data).to_string(index=False))
    print("=" * 115)
    
    # Detailed Tier Performance
    print("\nSpend Tier Level 4 Breakdown ($):")
    tier_rows = []
    for t_name, low, high in tier_definitions:
        t_mask = (test_amounts >= low) & (test_amounts < high)
        res_base = evaluate_tier_policy(test_probs[t_mask], test_amounts[t_mask], test_labels[t_mask], 1.0, 4.0, 0.03, 0.25, 0.35, 0.80, cfg_prod)
        res_lvl3 = evaluate_tier_policy(
            test_probs[t_mask], test_amounts[t_mask], test_labels[t_mask],
            lvl3_global_params["step_up_scale"], lvl3_global_params["decline_multiplier"],
            lvl3_global_params["min_step_up"], lvl3_global_params["max_step_up"],
            lvl3_global_params["min_decline"], lvl3_global_params["max_decline"], cfg_prod
        )
        res_lvl4 = strat3_tier_results[t_name]
        tier_rows.append({
            "Spend Tier": t_name,
            "Baseline Loss": f"${res_base['total_dollar_loss']:,.2f}",
            "Level 3 Loss": f"${res_lvl3['total_dollar_loss']:,.2f}",
            "Level 4 Loss": f"${res_lvl4['total_dollar_loss']:,.2f}",
            "Level 4 vs Base": f"+${res_base['total_dollar_loss'] - res_lvl4['total_dollar_loss']:,.2f}",
            "Level 4 vs Level 3": f"+${res_lvl3['total_dollar_loss'] - res_lvl4['total_dollar_loss']:,.2f}"
        })
    print(pd.DataFrame(tier_rows).to_string(index=False))
    print("=" * 115)
    
    # Save parameters for reference
    with open("models/level4_tiered_router_policy.json", "w") as f:
        json.dump(optimized_tier_params, f, indent=2)
    print("\nSaved Level 4 Tier Policy to models/level4_tiered_router_policy.json")

if __name__ == "__main__":
    run_level4_experiment()
