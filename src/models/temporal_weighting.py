import numpy as np

def compute_temporal_decay_weights(
    y: np.ndarray,
    timestamps: np.ndarray,
    half_life_days: float = 60.0,
    t_max: float = None
) -> np.ndarray:
    """
    Computes exponential temporal decay weights with dual-class invariant normalization.
    
    Formula:
        delta_days = (t_max - timestamp) / 86400.0
        raw_w_i = 2^(-delta_days / half_life_days)
        
    Dual-Class Invariant Normalization:
        sum_{i in fraud} w_i = N_fraud
        sum_{j in legit} w_j = N_legit
        
    This ensures zero perturbation to the effective class prior, preventing
    probability scale distortion while focusing tree splits on recent temporal patterns.
    """
    y = np.asarray(y, dtype=np.int32)
    timestamps = np.asarray(timestamps, dtype=np.float64)
    
    if t_max is None:
        t_max = np.max(timestamps)
        
    delta_days = np.maximum(0.0, (t_max - timestamps) / 86400.0)
    raw_weights = np.power(2.0, -delta_days / float(half_life_days))
    
    weights = np.empty_like(raw_weights)
    fraud_mask = (y == 1)
    legit_mask = (y == 0)
    
    n_fraud = np.sum(fraud_mask)
    n_legit = np.sum(legit_mask)
    
    sum_raw_fraud = np.sum(raw_weights[fraud_mask])
    sum_raw_legit = np.sum(raw_weights[legit_mask])
    
    if sum_raw_fraud > 0:
        weights[fraud_mask] = raw_weights[fraud_mask] * (n_fraud / sum_raw_fraud)
    else:
        weights[fraud_mask] = 1.0
        
    if sum_raw_legit > 0:
        weights[legit_mask] = raw_weights[legit_mask] * (n_legit / sum_raw_legit)
    else:
        weights[legit_mask] = 1.0
        
    return weights
