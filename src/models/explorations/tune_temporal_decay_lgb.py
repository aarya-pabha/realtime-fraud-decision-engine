import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import time
import numpy as np
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

from src.models.dataset_loader import get_temporal_splits, load_processed_dataset
from src.models.cost_router import DynamicCostRouter
from src.models.temporal_weighting import compute_temporal_decay_weights

def evaluate_predictions(y_true, preds, amounts, name="Model"):
    roc = roc_auc_score(y_true, preds)
    pr = average_precision_score(y_true, preds)
    brier = brier_score_loss(y_true, preds)
    
    # Financial loss with Level 3+4 Tiered Dynamic Cost Router
    router = DynamicCostRouter()
    routing = router.batch_route_and_evaluate(preds, amounts, actual_labels=y_true)
    
    loss = routing["total_financial_loss_dollars"]
    cb_ratio = routing["chargeback_ratio"] * 100.0
    declines = routing["decline_count"]
    step_ups = routing["step_up_count"]
    
    print(f"[{name}]")
    print(f"  ROC-AUC:  {roc:.4f}")
    print(f"  PR-AUC:   {pr:.4f}")
    print(f"  Brier:    {brier:.4f}")
    print(f"  Loss:     ${loss:,.2f}")
    print(f"  CB Ratio: {cb_ratio:.2f}%")
    print(f"  Declines: {declines:,} | Step-Ups: {step_ups:,}")
    return {
        "roc": roc, "pr": pr, "brier": brier,
        "loss": loss, "cb_ratio": cb_ratio,
        "declines": declines, "step_ups": step_ups
    }

def main():
    print("="*75)
    print("EMPIRICAL BENCHMARK: EXPONENTIAL TEMPORAL DECAY SAMPLE WEIGHTING")
    print("="*75)
    
    with open("models/best_params.json", "r") as f:
        best_params = json.load(f)
        
    print("Loading 3-way temporal partitions (Train: Days 1-120, Val: Days 121-150, Test: Days 151-183)...")
    df = load_processed_dataset()
    train_mask = df['TransactionDT'] < (120 * 86400)
    train_dt = df.loc[train_mask, 'TransactionDT'].values
    X_train, y_train, X_val, y_val, X_test, y_test, f_cols, c_cols = get_temporal_splits(df=df)
    
    test_amounts = X_test['TransactionAmt'].values
    val_amounts = X_val['TransactionAmt'].values
    
    # 0. Production Baseline Model
    print("\n--- 0. CURRENT PRODUCTION BASELINE (UNIFORM WEIGHTS) ---")
    base_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    val_base_preds = base_model.predict(X_val)
    test_base_preds = base_model.predict(X_test)
    base_val_res = evaluate_predictions(y_val, val_base_preds, val_amounts, "Baseline - Val Month 5")
    base_test_res = evaluate_predictions(y_test, test_base_preds, test_amounts, "Baseline - Test Month 6")
    
    # Evaluate 3 Half-Life Configurations: 60 Days (Primary), 45 Days, 90 Days
    half_lives = [60.0, 45.0, 90.0]
    results = {}
    
    for hl in half_lives:
        print(f"\n--- TRAINING WITH TEMPORAL DECAY (Half-Life = {hl:.0f} Days) ---")
        t0 = time.perf_counter()
        
        # Compute weights using raw TransactionDT
        weights = compute_temporal_decay_weights(
            y=y_train.values,
            timestamps=train_dt,
            half_life_days=hl,
            t_max=120.0 * 86400.0
        )
        
        # Verify dual-class invariance
        n_fraud = np.sum(y_train == 1)
        n_legit = np.sum(y_train == 0)
        sum_w_fraud = np.sum(weights[y_train == 1])
        sum_w_legit = np.sum(weights[y_train == 0])
        print(f"Dual-Class Invariance Check (Half-Life {hl:.0f}d):")
        print(f"  Fraud Weight Sum: {sum_w_fraud:,.1f} (Target: {n_fraud:,})")
        print(f"  Legit Weight Sum: {sum_w_legit:,.1f} (Target: {n_legit:,})")
        
        # Drop TransactionDT if it was temporarily retained in X_train
        dtrain = lgb.Dataset(X_train, label=y_train, weight=weights, free_raw_data=False)
        dval = lgb.Dataset(X_val, label=y_val, reference=dtrain, free_raw_data=False)
        
        params = {
            'objective': 'binary',
            'metric': ['auc', 'average_precision'],
            'boosting_type': 'gbdt',
            'verbosity': -1,
            'n_jobs': -1,
            'seed': 42,
            **best_params
        }
        
        model = lgb.train(
            params,
            dtrain,
            num_boost_round=250,
            valid_sets=[dtrain, dval],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
        )
        train_time = time.perf_counter() - t0
        print(f"Training completed in {train_time:.1f}s")
        
        val_preds = model.predict(X_val)
        test_preds = model.predict(X_test)
        
        val_res = evaluate_predictions(y_val, val_preds, val_amounts, f"Decay {hl:.0f}d - Val")
        test_res = evaluate_predictions(y_test, test_preds, test_amounts, f"Decay {hl:.0f}d - Test")
        
        results[hl] = {
            "model": model,
            "val": val_res,
            "test": test_res
        }
        
    print("\n" + "="*85)
    print("GUARDRAIL VERIFICATION MATRIX (MONTH 6 HOLDOUT TEST SET)")
    print("="*85)
    print(f"{'Configuration':<25} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'Brier':<8} | {'Total Loss':<12} | {'CB Ratio':<8}")
    print("-" * 85)
    print(f"{'0. Baseline (Uniform)':<25} | {base_test_res['pr']:<8.4f} | {base_test_res['roc']:<8.4f} | {base_test_res['brier']:<8.4f} | ${base_test_res['loss']:<11,.2f} | {base_test_res['cb_ratio']:<7.2f}%")
    
    for hl, res in results.items():
        t = res["test"]
        print(f"{f'Temporal Decay ({hl:.0f}d)':<25} | {t['pr']:<8.4f} | {t['roc']:<8.4f} | {t['brier']:<8.4f} | ${t['loss']:<11,.2f} | {t['cb_ratio']:<7.2f}%")
    print("="*85)

if __name__ == "__main__":
    main()
