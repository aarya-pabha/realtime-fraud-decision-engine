import sys
import os
sys.path.insert(0, os.path.abspath("."))

import optuna
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score
import json
import numpy as np
from src.models.dataset_loader import get_temporal_splits

def run_optuna_tuning(n_trials=25):
    """
    Executes Multi-Objective Optuna Hyperparameter Optimization on LightGBM.
    Expanded focused search space exploring high-capacity tree regimes (num_leaves 80-180, depth 9-16, colsample 0.75-0.98).
    Extracts the non-dominated Pareto frontier and selects winning parameters via Knee-Point Euclidean Distance.
    """
    os.makedirs("models", exist_ok=True)
    print("Loading 3-way temporal partitions (Train: Days 1-120, Val: Days 121-150)...")
    X_train, y_train, X_val, y_val, _, _, feature_cols, cat_cols = get_temporal_splits()
    
    print(f"Dataset Loaded: Train = {X_train.shape[0]:,} rows, Val = {X_val.shape[0]:,} rows across {len(feature_cols)} features.")
    dtrain = lgb.Dataset(X_train, label=y_train, params={'feature_pre_filter': False})
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain, params={'feature_pre_filter': False})
    
    def objective(trial):
        # Expanded focused search space around the winning high-capacity regime
        params = {
            'objective': 'binary',
            'metric': ['auc', 'average_precision'],
            'boosting_type': 'gbdt',
            'feature_pre_filter': False,
            'learning_rate': trial.suggest_float('learning_rate', 0.040, 0.095, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 80, 180),
            'max_depth': trial.suggest_int('max_depth', 9, 16),
            'min_child_samples': trial.suggest_int('min_child_samples', 80, 220),
            'subsample': trial.suggest_float('subsample', 0.75, 0.98),
            'subsample_freq': 1,
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.75, 0.98),
            'scale_pos_weight': trial.suggest_float('scale_pos_weight', 5.5, 13.5),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 2.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 3.0, log=True),
            'verbosity': -1,
            'n_jobs': -1,
            'seed': 42
        }
        
        model = lgb.train(
            params,
            dtrain,
            num_boost_round=200,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
        )
        
        preds = model.predict(X_val)
        roc_val = roc_auc_score(y_val, preds)
        pr_val = average_precision_score(y_val, preds)
        return pr_val, roc_val

    print(f"\nLaunching Expanded High-Capacity Optuna Study ({n_trials} trials)...")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        directions=["maximize", "maximize"],
        sampler=optuna.samplers.TPESampler(seed=42)
    )
    study.optimize(objective, n_trials=n_trials)
    
    # Pareto Frontier & Knee Selection
    pareto_trials = study.best_trials
    print(f"\nOptimization Complete! Identified {len(pareto_trials)} non-dominated Pareto optimal trials:")
    
    best_trial = None
    min_dist = float('inf')
    for trial in pareto_trials:
        pr, roc = trial.values
        dist = np.sqrt((1.0 - roc)**2 + (1.0 - pr)**2)
        print(f"  • Trial #{trial.number:02d}: PR-AUC = {pr:.4f}, ROC-AUC = {roc:.4f} (Euclidean Dist to Ideal = {dist:.4f})")
        if dist < min_dist:
            min_dist = dist
            best_trial = trial
            
    print("="*60)
    print(f"SELECTED OPERATIONAL KNEE-POINT TRIAL: #{best_trial.number}")
    print(f"Validation PR-AUC: {best_trial.values[0]:.4f} | Validation ROC-AUC: {best_trial.values[1]:.4f}")
    print("Winning Hyperparameter Set:")
    for k, v in best_trial.params.items():
        print(f"  {k}: {v}")
    print("="*60)
    
    with open("models/best_params.json", "w") as f:
        json.dump(best_trial.params, f, indent=2)
    print("Saved optimal hyperparameters to models/best_params.json.")
    return best_trial.params

if __name__ == "__main__":
    run_optuna_tuning()
