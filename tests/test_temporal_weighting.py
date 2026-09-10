import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from src.models.temporal_weighting import compute_temporal_decay_weights

def test_temporal_decay_monotonicity():
    # 5 timestamps spread across 100 days
    timestamps = np.array([0.0, 25.0 * 86400, 50.0 * 86400, 75.0 * 86400, 100.0 * 86400])
    y = np.array([0, 0, 1, 0, 1])
    
    weights = compute_temporal_decay_weights(y, timestamps, half_life_days=60.0)
    
    # Within class 0: weights should be monotonically increasing with time
    legit_weights = weights[y == 0]
    assert np.all(np.diff(legit_weights) > 0)
    
    # Within class 1: weights should be monotonically increasing with time
    fraud_weights = weights[y == 1]
    assert np.all(np.diff(fraud_weights) > 0)

def test_dual_class_invariance():
    np.random.seed(42)
    n = 1000
    y = np.random.choice([0, 1], size=n, p=[0.95, 0.05])
    timestamps = np.random.uniform(0, 120 * 86400, size=n)
    
    weights = compute_temporal_decay_weights(y, timestamps, half_life_days=60.0)
    
    n_fraud = np.sum(y == 1)
    n_legit = np.sum(y == 0)
    
    sum_w_fraud = np.sum(weights[y == 1])
    sum_w_legit = np.sum(weights[y == 0])
    
    # Dual-class invariant must hold to float precision
    assert np.isclose(sum_w_fraud, n_fraud, rtol=1e-5)
    assert np.isclose(sum_w_legit, n_legit, rtol=1e-5)
    assert np.isclose(sum_w_fraud / sum_w_legit, n_fraud / n_legit, rtol=1e-5)

def test_no_nans_or_negatives():
    y = np.array([0, 1, 0, 1])
    timestamps = np.array([1000.0, 2000.0, 3000.0, 4000.0])
    weights = compute_temporal_decay_weights(y, timestamps, half_life_days=60.0)
    
    assert not np.any(np.isnan(weights))
    assert np.all(weights > 0.0)
