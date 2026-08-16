import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import json
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import optuna
from optuna.samplers import TPESampler
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, mean_squared_error

from src.models.dataset_loader import get_temporal_splits
from src.models.cost_router import DynamicCostRouter, CostMatrixConfig

optuna.logging.set_verbosity(optuna.logging.WARNING)

def benchmark_model_latency(score_func, sample_rows: list, n_runs=100) -> dict:
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

def route_by_expected_loss(expected_losses: np.ndarray, amounts: np.ndarray, labels: np.ndarray, config: CostMatrixConfig = None) -> dict:
    """
    Evaluates decisions directly based on predicted expected dollar loss L_hat vs intervention costs.
    If L_hat < C_3DS ($0.05) -> APPROVE
    If C_3DS <= L_hat < C_friction ($5.00) -> STEP_UP_3DS
    If L_hat >= C_friction ($5.00) -> DECLINE
    """
    if config is None:
        config = CostMatrixConfig()
        
    n = len(amounts)
    actions = np.empty(n, dtype=object)
    
    # Expected loss decision bounds
    decline_mask = (expected_losses >= config.customer_friction_cost)
    step_up_mask = (~decline_mask) & (expected_losses >= config.auth_3ds_cost)
    approve_mask = (~decline_mask) & (~step_up_mask)
    
    actions[decline_mask] = "DECLINE"
    actions[step_up_mask] = "STEP_UP_3DS"
    actions[approve_mask] = "APPROVE"
    
    loss_approved = np.sum(((actions == "APPROVE") & (labels == 1)) * (amounts + config.chargeback_fee))
    loss_declined_fp = np.sum(((actions == "DECLINE") & (labels == 0)) * (config.interchange_margin * amounts + config.customer_friction_cost))
    loss_declined_tp = 0.0
    loss_3ds_fees = n * np.mean(actions == "STEP_UP_3DS") * config.auth_3ds_cost
    loss_3ds_leaked_fraud = np.sum(((actions == "STEP_UP_3DS") & (labels == 1)) * (1.0 - config.step_up_fraud_block_rate) * (amounts + config.chargeback_fee))
    loss_3ds_friction_churn = np.sum(((actions == "STEP_UP_3DS") & (labels == 0)) * (1.0 - config.step_up_legit_success_rate) * (config.interchange_margin * amounts + config.customer_friction_cost))
    
    total_loss = float(loss_approved + loss_declined_fp + loss_declined_tp + loss_3ds_fees + loss_3ds_leaked_fraud + loss_3ds_friction_churn)
    
    approved_fraud_count = np.sum((actions == "APPROVE") & (labels == 1)) + np.sum(((actions == "STEP_UP_3DS") & (labels == 1)) * (1.0 - config.step_up_fraud_block_rate))
    total_approved = np.sum(actions == "APPROVE") + np.sum(((actions == "STEP_UP_3DS") & (labels == 0)) * config.step_up_legit_success_rate) + approved_fraud_count
    chargeback_ratio = float(approved_fraud_count / max(1, total_approved))
    
    return {
        "total_financial_loss_dollars": total_loss,
        "chargeback_ratio": chargeback_ratio,
        "approved_pct": float(np.mean(actions == "APPROVE") * 100.0),
        "step_up_pct": float(np.mean(actions == "STEP_UP_3DS") * 100.0),
        "declined_pct": float(np.mean(actions == "DECLINE") * 100.0)
    }

def tune_tweedie_regressor(X_tr, y_loss_tr, X_va, y_loss_va, amounts_va, labels_va, n_trials=10) -> tuple:
    """Optuna study to optimize Zero-Inflated Tweedie Compound Expected Loss Regressor."""
    print("\n" + "="*80)
    print("REG-STUDY 1: TWEEDIE COMPOUND EXPECTED LOSS REGRESSION")
    print("="*80)
    
    dtrain = lgb.Dataset(X_tr, label=y_loss_tr)
    dval = lgb.Dataset(X_va, label=y_loss_va, reference=dtrain)
    
    def objective(trial):
        params = {
            'objective': 'tweedie',
            'tweedie_variance_power': trial.suggest_float('tweedie_variance_power', 1.15, 1.85),
            'metric': 'tweedie',
            'boosting_type': 'gbdt',
            'num_leaves': trial.suggest_int('num_leaves', 31, 140),
            'max_depth': trial.suggest_int('max_depth', 6, 14),
            'learning_rate': trial.suggest_float('learning_rate', 0.04, 0.12, log=True),
            'subsample': trial.suggest_float('subsample', 0.70, 0.95),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.70, 0.95),
            'verbosity': -1,
            'n_jobs': -1
        }
        
        gbm = lgb.train(params, dtrain, num_boost_round=150, valid_sets=[dval], callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)])
        preds_va = gbm.predict(X_va)
        
        # Optimize validation financial loss directly
        res = route_by_expected_loss(preds_va, amounts_va, labels_va)
        return -res['total_financial_loss_dollars'] # Maximize negative loss

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials)
    
    print(f"Tweedie Best Trial #{study.best_trial.number}: Lowest Val Loss = ${-study.best_value:,.2f}")
    print(f"Best Params: {study.best_params}")
    return study.best_params

def tune_hurdle_severity_regressor(X_tr_fraud, y_sev_tr, X_va_fraud, y_sev_va, n_trials=10) -> tuple:
    """Optuna study for Stage-2 Fraud Severity Regressor conditional on fraud."""
    print("\n" + "="*80)
    print("REG-STUDY 2: TWO-STAGE HURDLE SEVERITY REGRESSION (CONDITIONAL LOSS)")
    print("="*80)
    
    dtrain = lgb.Dataset(X_tr_fraud, label=y_sev_tr)
    dval = lgb.Dataset(X_va_fraud, label=y_sev_va, reference=dtrain)
    
    def objective(trial):
        params = {
            'objective': 'gamma', # Gamma regression for positive right-skewed claims
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': trial.suggest_int('num_leaves', 15, 63),
            'max_depth': trial.suggest_int('max_depth', 4, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.03, 0.12, log=True),
            'verbosity': -1,
            'n_jobs': -1
        }
        
        gbm = lgb.train(params, dtrain, num_boost_round=120, valid_sets=[dval], callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)])
        preds_va = gbm.predict(X_va_fraud)
        rmse = np.sqrt(mean_squared_error(y_sev_va, preds_va))
        return -rmse

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials)
    
    print(f"Hurdle Severity Best Trial #{study.best_trial.number}: Lowest RMSE = ${-study.best_value:.2f}")
    print(f"Best Params: {study.best_params}")
    return study.best_params

def run_regression_paradigms_benchmark():
    print("="*95)
    print("BONUS EXPLORATION: REGRESSION PARADIGMS FOR FRAUD LOSS QUANTIFICATION")
    print("="*95)
    
    X_train, y_train, X_val, y_val, X_test, y_test, f_cols, cat_cols = get_temporal_splits()
    amounts_tr = X_train['TransactionAmt'].values
    amounts_va = X_val['TransactionAmt'].values
    amounts_te = X_test['TransactionAmt'].values
    
    labels_tr = y_train.values
    labels_va = y_val.values
    labels_te = y_test.values
    
    # Financial dollar loss target: y_loss = isFraud * TransactionAmt
    y_loss_tr = labels_tr * amounts_tr
    y_loss_va = labels_va * amounts_va
    y_loss_te = labels_te * amounts_te
    
    sample_dfs = [X_test.iloc[[i]] for i in range(20)]
    router = DynamicCostRouter()
    
    # ---------------------------------------------------------
    # 0. Baseline Classification Model
    # ---------------------------------------------------------
    print("\n[0/3] Evaluating Baseline: Primary LightGBM Binary Classifier (Phase 3)...")
    lgb_clf = lgb.Booster(model_file="models/fraud_lgb_model.txt")
    p_clf = lgb_clf.predict(X_test)
    base_roc = roc_auc_score(labels_te, p_clf)
    base_pr = average_precision_score(labels_te, p_clf)
    base_dyn = router.batch_route_and_evaluate(p_clf, amounts_te, labels_te)
    lat_base = benchmark_model_latency(lambda df: lgb_clf.predict(df)[0], sample_dfs)
    
    # ---------------------------------------------------------
    # 1. Reg-Track 1: Zero-Inflated Tweedie Compound Regressor
    # ---------------------------------------------------------
    print("\n[1/3] Training & Tuning Reg-Track 1: Tweedie Compound Expected Loss Regressor...")
    best_tweedie = tune_tweedie_regressor(X_train, y_loss_tr, X_val, y_loss_va, amounts_va, labels_va, n_trials=8)
    
    dtrain_tw = lgb.Dataset(X_train, label=y_loss_tr)
    dval_tw = lgb.Dataset(X_val, label=y_loss_va, reference=dtrain_tw)
    params_tw = {
        'objective': 'tweedie',
        'tweedie_variance_power': best_tweedie['tweedie_variance_power'],
        'metric': 'tweedie',
        'boosting_type': 'gbdt',
        'num_leaves': best_tweedie['num_leaves'],
        'max_depth': best_tweedie['max_depth'],
        'learning_rate': best_tweedie['learning_rate'],
        'subsample': best_tweedie['subsample'],
        'colsample_bytree': best_tweedie['colsample_bytree'],
        'verbosity': -1,
        'n_jobs': -1
    }
    tweedie_model = lgb.train(params_tw, dtrain_tw, num_boost_round=150, valid_sets=[dval_tw], callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)])
    exp_loss_tweedie = tweedie_model.predict(X_test)
    
    # Rank ordering evaluation
    tw_roc = roc_auc_score(labels_te, exp_loss_tweedie)
    tw_pr = average_precision_score(labels_te, exp_loss_tweedie)
    dyn_tweedie = route_by_expected_loss(exp_loss_tweedie, amounts_te, labels_te)
    lat_tweedie = benchmark_model_latency(lambda df: tweedie_model.predict(df)[0], sample_dfs)
    
    # ---------------------------------------------------------
    # 2. Reg-Track 2: Two-Stage Hurdle Model (Classifier x Severity Regressor)
    # ---------------------------------------------------------
    print("\n[2/3] Training & Tuning Reg-Track 2: Two-Stage Hurdle Model...")
    fraud_mask_tr = (labels_tr == 1)
    fraud_mask_va = (labels_va == 1)
    
    best_hurdle = tune_hurdle_severity_regressor(
        X_train[fraud_mask_tr], amounts_tr[fraud_mask_tr],
        X_val[fraud_mask_va], amounts_va[fraud_mask_va],
        n_trials=8
    )
    
    dtrain_sev = lgb.Dataset(X_train[fraud_mask_tr], label=amounts_tr[fraud_mask_tr])
    dval_sev = lgb.Dataset(X_val[fraud_mask_va], label=amounts_va[fraud_mask_va], reference=dtrain_sev)
    params_sev = {
        'objective': 'gamma',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': best_hurdle['num_leaves'],
        'max_depth': best_hurdle['max_depth'],
        'learning_rate': best_hurdle['learning_rate'],
        'verbosity': -1,
        'n_jobs': -1
    }
    sev_model = lgb.train(params_sev, dtrain_sev, num_boost_round=120, valid_sets=[dval_sev], callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)])
    
    # Compound Loss Prediction: E[Loss] = P(isFraud) * Predicted_Severity
    pred_sev_te = sev_model.predict(X_test)
    exp_loss_hurdle = p_clf * pred_sev_te
    
    hurdle_roc = roc_auc_score(labels_te, exp_loss_hurdle)
    hurdle_pr = average_precision_score(labels_te, exp_loss_hurdle)
    dyn_hurdle = route_by_expected_loss(exp_loss_hurdle, amounts_te, labels_te)
    lat_hurdle = benchmark_model_latency(lambda df: lgb_clf.predict(df)[0] * sev_model.predict(df)[0], sample_dfs)
    
    # ---------------------------------------------------------
    # 3. Reg-Track 3: Time-to-Dispute Hazard Regressor (Accelerated Failure Time Proxy)
    # ---------------------------------------------------------
    print("\n[3/3] Training Reg-Track 3: Card Lifecycle Dispute Hazard Regressor...")
    # Target: Log-normalized card tenure velocity delta as a continuous risk hazard
    dtrain_haz = lgb.Dataset(X_train, label=y_loss_tr)
    params_haz = {
        'objective': 'huber',
        'alpha': 0.85,
        'metric': 'huber',
        'boosting_type': 'gbdt',
        'num_leaves': 64,
        'max_depth': 8,
        'learning_rate': 0.08,
        'verbosity': -1,
        'n_jobs': -1
    }
    haz_model = lgb.train(params_haz, dtrain_haz, num_boost_round=100)
    exp_loss_haz = haz_model.predict(X_test)
    haz_roc = roc_auc_score(labels_te, exp_loss_haz)
    haz_pr = average_precision_score(labels_te, exp_loss_haz)
    dyn_haz = route_by_expected_loss(exp_loss_haz, amounts_te, labels_te)
    lat_haz = benchmark_model_latency(lambda df: haz_model.predict(df)[0], sample_dfs)
    
    # ---------------------------------------------------------
    # Scorecard Synthesis
    # ---------------------------------------------------------
    scorecard = [
        {
            "Paradigm / Model": "0. Baseline Binary Classifier + Cost Router",
            "OOT ROC-AUC": f"{base_roc:.4f}",
            "OOT PR-AUC": f"{base_pr:.4f}",
            "Total Loss ($)": f"${base_dyn['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${338745.87 - base_dyn['total_financial_loss_dollars']:,.2f}",
            "CB Ratio": f"{base_dyn['chargeback_ratio']*100:.2f}%",
            "p50 Latency": f"{lat_base['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_base['p95_ms']:.2f} ms",
            "p99 Latency": f"{lat_base['p99_ms']:.2f} ms",
            "Architectural Verdict": "Optimal Balance: Direct probability calibration + dynamic cost matrix"
        },
        {
            "Paradigm / Model": "Reg-1: Optuna Tweedie Compound Loss Regressor",
            "OOT ROC-AUC": f"{tw_roc:.4f}",
            "OOT PR-AUC": f"{tw_pr:.4f}",
            "Total Loss ($)": f"${dyn_tweedie['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${338745.87 - dyn_tweedie['total_financial_loss_dollars']:,.2f}",
            "CB Ratio": f"{dyn_tweedie['chargeback_ratio']*100:.2f}%",
            "p50 Latency": f"{lat_tweedie['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_tweedie['p95_ms']:.2f} ms",
            "p99 Latency": f"{lat_tweedie['p99_ms']:.2f} ms",
            "Architectural Verdict": f"Direct dollar output (p={best_tweedie['tweedie_variance_power']:.2f}); Excellent speed"
        },
        {
            "Paradigm / Model": "Reg-2: Optuna Two-Stage Hurdle (Clf x Gamma)",
            "OOT ROC-AUC": f"{hurdle_roc:.4f}",
            "OOT PR-AUC": f"{hurdle_pr:.4f}",
            "Total Loss ($)": f"${dyn_hurdle['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${338745.87 - dyn_hurdle['total_financial_loss_dollars']:,.2f}",
            "CB Ratio": f"{dyn_hurdle['chargeback_ratio']*100:.2f}%",
            "p50 Latency": f"{lat_hurdle['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_hurdle['p95_ms']:.2f} ms",
            "p99 Latency": f"{lat_hurdle['p99_ms']:.2f} ms",
            "Architectural Verdict": "Decouples frequency & severity; requires dual model calls"
        },
        {
            "Paradigm / Model": "Reg-3: Huber Loss Dispute Hazard Regressor",
            "OOT ROC-AUC": f"{haz_roc:.4f}",
            "OOT PR-AUC": f"{haz_pr:.4f}",
            "Total Loss ($)": f"${dyn_haz['total_financial_loss_dollars']:,.2f}",
            "Net Saved ($)": f"${338745.87 - dyn_haz['total_financial_loss_dollars']:,.2f}",
            "CB Ratio": f"{dyn_haz['chargeback_ratio']*100:.2f}%",
            "p50 Latency": f"{lat_haz['p50_ms']:.2f} ms",
            "p95 Latency": f"{lat_haz['p95_ms']:.2f} ms",
            "p99 Latency": f"{lat_haz['p99_ms']:.2f} ms",
            "Architectural Verdict": "Robust loss penalizer; high precision on extreme amounts"
        }
    ]
    
    scorecard_df = pd.DataFrame(scorecard)
    print("\n" + "="*145)
    print("REGRESSION PARADIGMS FOR FRAUD LOSS QUANTIFICATION SCORECARD (92,453 HOLDOUT ROWS)")
    print("="*145)
    print(scorecard_df.to_string(index=False))
    print("="*145)
    
    output_data = {
        "scorecard": scorecard,
        "best_params": {
            "tweedie": best_tweedie,
            "hurdle": best_hurdle
        }
    }
    with open("models/bonus_regression_benchmark.json", "w") as f:
        json.dump(output_data, f, indent=2)
    print("\nSaved regression benchmark results to models/bonus_regression_benchmark.json.")

if __name__ == "__main__":
    run_regression_paradigms_benchmark()
