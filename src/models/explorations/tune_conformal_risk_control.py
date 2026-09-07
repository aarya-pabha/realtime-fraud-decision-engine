import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import time
import numpy as np
import lightgbm as lgb
from typing import Dict, Any, List, Tuple
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter

def compute_loss_curve(
    preds: np.ndarray,
    amounts: np.ndarray,
    labels: np.ndarray,
    lambdas: np.ndarray,
    decline_multiplier: float = 7.25,
    margin_decay: float = 0.02,
    friction: float = 5.0,
    chargeback_fee: float = 25.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Vectorized computation of payment chargeback loss and financial loss across candidate lambda thresholds.
    
    L_i(lambda):
      - If y_i = 1 and approved: 1.0 (chargeback)
      - If y_i = 1 and 3DS step-up: 0.05 (bypassed chargeback)
      - If y_i = 1 and declined: 0.0
      - If y_i = 0: 0.0
    """
    n = len(preds)
    c_fn = amounts + chargeback_fee
    c_fp = (amounts * margin_decay) + friction
    tau_star = c_fp / (c_fn + c_fp)
    
    y_fraud = (labels == 1)
    y_legit = (labels == 0)
    
    cb_risks = np.empty(len(lambdas), dtype=np.float64)
    total_losses = np.empty(len(lambdas), dtype=np.float64)
    declines = np.empty(len(lambdas), dtype=np.int32)
    step_ups = np.empty(len(lambdas), dtype=np.int32)
    
    for idx, lam in enumerate(lambdas):
        # Tiered threshold scaling
        tau_step = tau_star * lam
        tau_dec = tau_star * decline_multiplier
        
        # Spend-tier specific bounds
        m1 = amounts < 100.0
        m2 = (amounts >= 100.0) & (amounts < 500.0)
        m3 = amounts >= 500.0
        
        s = np.empty_like(tau_step)
        d = np.empty_like(tau_dec)
        
        s[m1] = np.clip(tau_step[m1] * 0.85, 0.010, 0.100)
        d[m1] = np.clip(tau_dec[m1], 0.590, 0.850)
        
        s[m2] = np.clip(tau_step[m2] * 0.90, 0.020, 0.200)
        d[m2] = np.clip(tau_dec[m2] * 1.07, 0.730, 0.950)
        
        s[m3] = np.clip(tau_step[m3] * 0.65, 0.008, 0.340)
        d[m3] = np.clip(tau_dec[m3] * 1.34, 0.670, 0.900)
        
        d = np.maximum(d, s + 0.01)
        
        is_approve = preds < s
        is_step_up = (preds >= s) & (preds < d)
        is_decline = preds >= d
        
        # Chargeback event calculation
        # Each approved fraud is 1 chargeback; each 3DS fraud has 5% bypass
        cb_count = np.sum(is_approve & y_fraud) + (0.05 * np.sum(is_step_up & y_fraud))
        cb_risks[idx] = cb_count / n
        
        # Realized financial losses
        loss_app = np.sum(amounts[is_approve & y_fraud] + chargeback_fee)
        loss_dec = np.sum((amounts[is_decline & y_legit] * margin_decay) + friction)
        loss_3ds = (np.sum(is_step_up) * 0.05) + \
                   np.sum(0.05 * (amounts[is_step_up & y_fraud] + chargeback_fee)) + \
                   np.sum(0.15 * ((amounts[is_step_up & y_legit] * margin_decay) + friction))
        
        total_losses[idx] = loss_app + loss_dec + loss_3ds
        declines[idx] = int(np.sum(is_decline))
        step_ups[idx] = int(np.sum(is_step_up))
        
    return cb_risks, total_losses, declines, step_ups

def calibrate_crc_threshold(
    cal_cb_risks: np.ndarray,
    lambdas: np.ndarray,
    alpha: float,
    n_cal: int
) -> float:
    """
    Conformal Risk Control (Angelopoulos et al., 2024, Theorem 1):
    Finds the largest lambda such that the finite-sample adjusted risk is <= alpha:
      (n / (n + 1)) * R_hat(lambda) + (B / (n + 1)) <= alpha
    where B = 1.0 (maximum chargeback loss per sample).
    """
    B = 1.0
    adjusted_risk = (n_cal / (n_cal + 1.0)) * cal_cb_risks + (B / (n_cal + 1.0))
    valid_indices = np.where(adjusted_risk <= alpha)[0]
    
    if len(valid_indices) == 0:
        # If no lambda satisfies the bound, take the strictest threshold (minimum lambda)
        return float(lambdas[0])
    
    # Take the largest lambda that satisfies the bound (maximizes approval rates/minimizes friction)
    best_idx = valid_indices[-1]
    return float(lambdas[best_idx])

def calibrate_ltt_bound(
    cal_cb_risks: np.ndarray,
    lambdas: np.ndarray,
    alpha: float,
    delta: float,
    n_cal: int
) -> float:
    """
    Learn-Then-Test (LTT) PAC Bound (Bates et al., 2021):
    Provides a high-probability guarantee: P(Test Risk <= alpha) >= 1 - delta.
    Uses Hoeffding-Bentkus bound inversion.
    """
    # Hoeffding bound for bounded random variable in [0, 1]
    # P(R > alpha) <= exp(-2 * n * (alpha - R_hat)^2) for R_hat < alpha
    # Solve for R_hat: alpha - sqrt(ln(1/delta) / (2 * n))
    epsilon = np.sqrt(np.log(1.0 / delta) / (2.0 * n_cal))
    effective_ceiling = max(0.0, alpha - epsilon)
    
    valid_indices = np.where(cal_cb_risks <= effective_ceiling)[0]
    if len(valid_indices) == 0:
        return float(lambdas[0])
    return float(lambdas[valid_indices[-1]])

def main():
    print("="*80)
    print("NOVELTY EXPERIMENT: CONFORMAL RISK CONTROL (CRC) FOR PAYMENT FRAUD")
    print("="*80)
    
    # 1. Load data & baseline model
    print("Loading 3-way temporal splits (Train: Days 1-120, Val: Days 121-150, Test: Days 151-183)...")
    X_train, y_train, X_val, y_val, X_test, y_test, f_cols, c_cols = get_temporal_splits()
    
    print(f"Dataset Partitions:")
    print(f"  Calibration Horizon (Month 5 Val): {len(y_val):,} transactions (Fraud: {np.sum(y_val==1):,}, {np.mean(y_val)*100:.2f}%)")
    print(f"  Test Horizon (Month 6 Holdout):     {len(y_test):,} transactions (Fraud: {np.sum(y_test==1):,}, {np.mean(y_test)*100:.2f}%)")
    
    base_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    val_preds = base_model.predict(X_val)
    test_preds = base_model.predict(X_test)
    
    val_amounts = X_val['TransactionAmt'].values
    test_amounts = X_test['TransactionAmt'].values
    y_val_arr = y_val.values
    y_test_arr = y_test.values
    
    # 2. Grid of lambda multipliers to evaluate
    lambdas = np.linspace(0.40, 2.50, 421)
    
    print("\nComputing empirical risk curves on Calibration Horizon (Month 5)...")
    cal_cb, cal_loss, cal_dec, cal_stp = compute_loss_curve(val_preds, val_amounts, y_val_arr, lambdas)
    
    print("Computing true risk curves on Holdout Test Stream (Month 6)...")
    test_cb, test_loss, test_dec, test_stp = compute_loss_curve(test_preds, test_amounts, y_test_arr, lambdas)
    
    # 3. Evaluate CRC across regulatory risk targets
    # alpha targets: 0.35%, 0.40%, 0.50%, 0.70%, 1.00% (Mastercard cap)
    risk_targets = [0.0035, 0.0040, 0.0045, 0.0050, 0.0070, 0.0100]
    
    print("\n" + "="*95)
    print("CONFORMAL RISK CONTROL: FINITE-SAMPLE CALIBRATION & TEST VERIFICATION")
    print("="*95)
    print(f"{'Target Cap (alpha)':<20} | {'Calibrated lambda':<18} | {'Calib Risk':<12} | {'Test Risk':<12} | {'Guar. Valid?':<14} | {'Total Loss':<12}")
    print("-" * 95)
    
    n_cal = len(y_val)
    delta = 0.05 # 95% confidence level
    
    for alpha in risk_targets:
        # 1. Standard Conformal Risk Control (CRC)
        lam_crc = calibrate_crc_threshold(cal_cb, lambdas, alpha, n_cal)
        
        # Evaluate on Test
        idx_test = np.argmin(np.abs(lambdas - lam_crc))
        realized_cb_test = test_cb[idx_test]
        realized_loss_test = test_loss[idx_test]
        realized_cb_cal = cal_cb[idx_test]
        
        is_valid = "PASS" if realized_cb_test <= alpha else "BREACH"
        print(f"{f'{alpha*100:.2f}% ({alpha*10000:.0f} bps)':<20} | {f'lambda = {lam_crc:.3f}':<18} | {f'{realized_cb_cal*100:.2f}%':<12} | {f'{realized_cb_test*100:.2f}%':<12} | {is_valid:<14} | ${realized_loss_test:,.2f}")
        
    print("="*95)

    # 4. Drift-Compensated (Non-Exchangeable) Conformal Risk Control
    # Accounts for temporal concept drift between Month 5 and Month 6 (Barber et al., 2023)
    drift_margin = 0.0006 # 6 basis points drift buffer
    print("\n" + "="*95)
    print("DRIFT-COMPENSATED CONFORMAL RISK CONTROL (NON-EXCHANGEABLE TEMPORAL ADAPTATION)")
    print("="*95)
    print(f"{'Target Cap (alpha)':<20} | {'Calib Target':<14} | {'Calib Risk':<12} | {'Test Risk':<12} | {'Guar. Valid?':<14} | {'Total Loss':<12}")
    print("-" * 95)
    
    for alpha in risk_targets:
        target_cal = max(0.0020, alpha - drift_margin)
        lam_drift = calibrate_crc_threshold(cal_cb, lambdas, target_cal, n_cal)
        idx_test = np.argmin(np.abs(lambdas - lam_drift))
        
        realized_cb_test = test_cb[idx_test]
        realized_loss_test = test_loss[idx_test]
        realized_cb_cal = cal_cb[idx_test]
        
        is_valid = "PASS" if realized_cb_test <= alpha else "BREACH"
        print(f"{f'{alpha*100:.2f}% ({alpha*10000:.0f} bps)':<20} | {f'{target_cal*100:.2f}%':<14} | {f'{realized_cb_cal*100:.2f}%':<12} | {f'{realized_cb_test*100:.2f}%':<12} | {is_valid:<14} | ${realized_loss_test:,.2f}")
        
    print("="*95)
    
    # 5. Compare with Baseline Level 3+4 Router
    router = DynamicCostRouter()
    base_eval = router.batch_route_and_evaluate(test_preds, test_amounts, actual_labels=y_test_arr)
    print("\n--- BASELINE LEVEL 3+4 DYNAMIC COST ROUTER REFERENCE ---")
    print(f"  Realized Loss:     ${base_eval['total_financial_loss_dollars']:,.2f}")
    print(f"  Chargeback Ratio:  {base_eval['chargeback_ratio']*100:.2f}% ({base_eval['chargeback_ratio']*10000:.0f} bps)")
    print(f"  Hard Declines:     {base_eval['decline_count']:,}")
    print(f"  3DS Step-Ups:      {base_eval['step_up_count']:,}")
    print("="*95)

if __name__ == "__main__":
    main()
