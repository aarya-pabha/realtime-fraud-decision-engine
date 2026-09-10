import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
import time
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

from src.models.dataset_loader import get_temporal_splits, V_MEDOID_COLS
from src.models.cost_router import DynamicCostRouter

def evaluate_predictions(y_true, preds, amounts, name="Model"):
    roc = roc_auc_score(y_true, preds)
    pr = average_precision_score(y_true, preds)
    brier = brier_score_loss(y_true, preds)
    
    # Financial loss with production cost router
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
    print("="*70)
    print("INVESTIGATING TECHNIQUES TO IMPROVE PR-AUC WITHOUT DEGRADING SYSTEM")
    print("="*70)
    
    with open("models/best_params.json", "r") as f:
        best_params = json.load(f)
        
    print("Loading temporal splits...")
    X_train, y_train, X_val, y_val, X_test, y_test, f_cols, c_cols = get_temporal_splits()
    
    test_amounts = X_test['TransactionAmt'].values
    val_amounts = X_val['TransactionAmt'].values
    
    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
    
    # Baseline Model
    print("\n--- 0. CURRENT PRODUCTION BASELINE ---")
    base_model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    val_base_preds = base_model.predict(X_val)
    test_base_preds = base_model.predict(X_test)
    base_val_res = evaluate_predictions(y_val, val_base_preds, val_amounts, "Baseline - Val Month 5")
    base_test_res = evaluate_predictions(y_test, test_base_preds, test_amounts, "Baseline - Test Month 6")
    
    # -------------------------------------------------------------
    # Experiment 1: Early Stopping on Average Precision (PR-AUC)
    # -------------------------------------------------------------
    print("\n--- 1. EARLY STOPPING TARGETING AVERAGE PRECISION (PR-AUC) ---")
    params_ap = {
        'objective': 'binary',
        'metric': ['average_precision', 'auc'],
        'first_metric_only': True,
        'boosting_type': 'gbdt',
        'verbosity': -1,
        'n_jobs': -1,
        'seed': 42,
        **best_params
    }
    model_ap = lgb.train(
        params_ap,
        dtrain,
        num_boost_round=350,
        valid_sets=[dtrain, dval],
        callbacks=[lgb.early_stopping(stopping_rounds=35, verbose=False)]
    )
    val_ap_preds = model_ap.predict(X_val)
    test_ap_preds = model_ap.predict(X_test)
    ap_val_res = evaluate_predictions(y_val, val_ap_preds, val_amounts, "Exp 1 (AP-Stopping) - Val")
    ap_test_res = evaluate_predictions(y_test, test_ap_preds, test_amounts, "Exp 1 (AP-Stopping) - Test")
    
    # -------------------------------------------------------------
    # Experiment 2: Regularized Learning Rate with More Rounds
    # -------------------------------------------------------------
    print("\n--- 2. LEARNING RATE SHRINKAGE (lr=0.03, num_rounds=400) ---")
    params_lr = {
        'objective': 'binary',
        'metric': ['average_precision', 'auc'],
        'first_metric_only': True,
        'boosting_type': 'gbdt',
        'verbosity': -1,
        'n_jobs': -1,
        'seed': 42,
        **best_params,
        'learning_rate': 0.030,
        'num_leaves': 180,
    }
    model_lr = lgb.train(
        params_lr,
        dtrain,
        num_boost_round=450,
        valid_sets=[dtrain, dval],
        callbacks=[lgb.early_stopping(stopping_rounds=40, verbose=False)]
    )
    val_lr_preds = model_lr.predict(X_val)
    test_lr_preds = model_lr.predict(X_test)
    lr_val_res = evaluate_predictions(y_val, val_lr_preds, val_amounts, "Exp 2 (LR Shrinkage) - Val")
    lr_test_res = evaluate_predictions(y_test, test_lr_preds, test_amounts, "Exp 2 (LR Shrinkage) - Test")
    
    # -------------------------------------------------------------
    # Experiment 3: Feature Enhancement (amt_diff_mean_card + card count)
    # -------------------------------------------------------------
    print("\n--- 3. FEATURE ENGINEERING: Spend Deviation & Entity Counts ---")
    from src.models.dataset_loader import load_processed_dataset
    df = load_processed_dataset()
    
    # Add new high-signal features:
    # 1. amt_diff_mean_card = TransactionAmt - card_amt_mean
    # 2. card_base_id_count = log1p(count of transactions per card_base_id)
    card_stats = df.groupby('card_base_id')['TransactionAmt'].agg(['mean', 'count']).reset_index()
    card_stats.columns = ['card_base_id', 'card_amt_mean_new', 'card_tx_count']
    df = df.merge(card_stats, on='card_base_id', how='left')
    df['amt_diff_mean_card'] = df['TransactionAmt'] - df['card_amt_mean_new']
    df['log_card_tx_count'] = np.log1p(df['card_tx_count'])
    
    # Also TransactionAmt to addr1 mean
    addr_stats = df.groupby('addr1')['TransactionAmt'].mean().reset_index()
    addr_stats.columns = ['addr1', 'addr1_amt_mean']
    df = df.merge(addr_stats, on='addr1', how='left')
    df['amt_diff_mean_addr1'] = df['TransactionAmt'] - df['addr1_amt_mean'].fillna(df['TransactionAmt'].mean())
    
    df.drop(columns=['card_amt_mean_new', 'card_tx_count', 'addr1_amt_mean'], inplace=True, errors='ignore')
    
    # New feature cols
    new_features = ['amt_diff_mean_card', 'log_card_tx_count', 'amt_diff_mean_addr1']
    extended_feature_cols = f_cols + new_features
    
    train_mask = df['TransactionDT'] < (120 * 86400)
    val_mask = (df['TransactionDT'] >= (120 * 86400)) & (df['TransactionDT'] < (151 * 86400))
    test_mask = df['TransactionDT'] >= (151 * 86400)
    
    X_train_ext = df.loc[train_mask, extended_feature_cols]
    y_train_ext = df.loc[train_mask, 'isFraud']
    X_val_ext = df.loc[val_mask, extended_feature_cols]
    y_val_ext = df.loc[val_mask, 'isFraud']
    X_test_ext = df.loc[test_mask, extended_feature_cols]
    y_test_ext = df.loc[test_mask, 'isFraud']
    
    for c in c_cols:
        if c in X_train_ext.columns:
            X_train_ext[c] = X_train_ext[c].astype('category')
            X_val_ext[c] = X_val_ext[c].astype('category')
            X_test_ext[c] = X_test_ext[c].astype('category')
            
    dtrain_ext = lgb.Dataset(X_train_ext, label=y_train_ext)
    dval_ext = lgb.Dataset(X_val_ext, label=y_val_ext, reference=dtrain_ext)
    
    model_feat = lgb.train(
        params_ap,
        dtrain_ext,
        num_boost_round=350,
        valid_sets=[dtrain_ext, dval_ext],
        callbacks=[lgb.early_stopping(stopping_rounds=35, verbose=False)]
    )
    val_feat_preds = model_feat.predict(X_val_ext)
    test_feat_preds = model_feat.predict(X_test_ext)
    feat_val_res = evaluate_predictions(y_val_ext, val_feat_preds, val_amounts, "Exp 3 (Features + AP-Stopping) - Val")
    feat_test_res = evaluate_predictions(y_test_ext, test_feat_preds, test_amounts, "Exp 3 (Features + AP-Stopping) - Test")
    
    print("\n" + "="*70)
    print("SUMMARY COMPARISON (TEST SET - MONTH 6)")
    print("="*70)
    print(f"{'Method':<35} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'Brier':<8} | {'Total Loss':<12}")
    print("-" * 75)
    print(f"{'0. Baseline':<35} | {base_test_res['pr']:<8.4f} | {base_test_res['roc']:<8.4f} | {base_test_res['brier']:<8.4f} | ${base_test_res['loss']:<11,.2f}")
    print(f"{'1. AP Early Stopping':<35} | {ap_test_res['pr']:<8.4f} | {ap_test_res['roc']:<8.4f} | {ap_test_res['brier']:<8.4f} | ${ap_test_res['loss']:<11,.2f}")
    print(f"{'2. LR Shrinkage + AP Stopping':<35} | {lr_test_res['pr']:<8.4f} | {lr_test_res['roc']:<8.4f} | {lr_test_res['brier']:<8.4f} | ${lr_test_res['loss']:<11,.2f}")
    print(f"{'3. Engineered Features + AP':<35} | {feat_test_res['pr']:<8.4f} | {feat_test_res['roc']:<8.4f} | {feat_test_res['brier']:<8.4f} | ${feat_test_res['loss']:<11,.2f}")
    print("="*70)

if __name__ == "__main__":
    main()
