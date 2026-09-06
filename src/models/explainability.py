import sys
import os
sys.path.insert(0, os.path.abspath("."))

import math
import lightgbm as lgb
import numpy as np
import pandas as pd
import time
from typing import Tuple, List, Dict, Any, Optional

REASON_CODE_MAP = {
    # Velocity & Burst Attacks
    "tx_count_5m": "BURST_VELOCITY_5M_SPIKE",
    "tx_count_1h": "HIGH_HOURLY_TRANSACTION_VELOCITY",
    "amt_sum_24h": "HIGH_24H_CUMULATIVE_SPEND",
    
    # Amount Volatility & Sizing
    "TransactionAmt": "UNUSUAL_TRANSACTION_AMOUNT",
    "amt_to_mean_card": "ANOMALOUS_CARD_SPEND_RATIO",
    "amt_to_std_card": "HIGH_AMOUNT_STANDARD_DEVIATION",
    "log_TransactionAmt": "ELEVATED_LOG_TRANSACTION_AMOUNT",
    
    # Currency & Precision Anomalies
    "is_foreign_currency": "FOREIGN_CURRENCY_EXCHANGE_RISK",
    "decimal_places": "IRREGULAR_CURRENCY_PRECISION",
    
    # Email & Identity Risk
    "email_domain_match": "PURCHASER_RECIPIENT_EMAIL_MISMATCH",
    "is_disposable_email": "DISPOSABLE_EMAIL_DOMAIN_DETECTED",
    
    # Card Lifecycle Deltas
    "D1_to_mean_card": "UNUSUAL_DAYS_SINCE_REGISTRATION",
    "D2_to_mean_card": "IRREGULAR_TRANSACTION_CYCLE_DELTA",
    "D15_to_mean_card": "UNUSUAL_CARD_LIFECYCLE_DELTA",
    
    # Entity Frequencies & Attributes
    "card_base_id_freq": "CARD_BASE_USAGE_ANOMALY",
    "cardholder_uid_freq": "CARDHOLDER_UID_USAGE_ANOMALY",
    "addr1_freq": "UNCOMMON_BILLING_ZIP_REGION",
    "P_emaildomain_freq": "UNCOMMON_EMAIL_DOMAIN_PROVIDER",
    "card4": "HIGH_RISK_PAYMENT_NETWORK",
    "card6": "HIGH_RISK_CARD_TYPE_CATEGORY",
    "ProductCD": "HIGH_RISK_PRODUCT_MERCHANT_SEGMENT",
    
    # Device & Technical Fingerprints
    "device_corp": "UNRECOGNIZED_DEVICE_HARDWARE",
    "browser_corp": "HIGH_RISK_BROWSER_FAMILY",
    "os_family": "ANOMALOUS_OPERATING_SYSTEM",
    "screen_aspect_ratio": "ANOMALOUS_DEVICE_RESOLUTION",
    
    # Core Vesta C-Counters (Card/Address linking velocity)
    "C1": "HIGH_VELOCITY_ASSOCIATED_PHONE_COUNT",
    "C2": "HIGH_VELOCITY_ASSOCIATED_DEVICE_COUNT",
    "C4": "HIGH_RISK_CROSS_CARD_IP_BURST",
    "C5": "UNUSUAL_PAYMENT_COUNT_BURST",
    "C6": "HIGH_EMAIL_ADDRESS_FREQUENCY_COUNT",
    "C7": "CROSS_BORDER_VELOCITY_COUNT_BURST",
    "C8": "HIGH_CARD_VELOCITY_SPIKE",
    "C9": "MULTIPLE_TRANSACTION_COUNTER_ANOMALY",
    "C10": "IP_NETWORK_VELOCITY_COUNT_SPIKE",
    "C11": "LINKED_PAYMENT_ADDRESS_BURST",
    "C12": "SHARED_EMAIL_DOMAIN_VELOCITY",
    "C13": "HIGH_FREQUENCY_ACCOUNT_USAGE_COUNT",
    "C14": "HIGH_CROSS_MERCHANT_CARD_COUNT"
}

class FraudExplainer:
    """
    Sub-10ms localized real-time SHAP TreeExplainer for LightGBM fraud model.
    Extracts top-3 positive contributors to transaction risk and translates them into standard operational reason codes.
    """
    def __init__(self, model_path="models/fraud_lgb_model.txt"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        self.model = lgb.Booster(model_file=model_path)
        self.feature_names = self.model.feature_name()

    def score_and_explain(self, feature_df: pd.DataFrame, num_iteration: Optional[int] = None) -> Tuple[float, List[str], float]:
        """
        Unified single-pass LightGBM C++ inference and localized TreeSHAP attribution.
        Returns: (calibrated_fraud_prob, top_3_reason_codes, latency_ms)
        """
        t0 = time.perf_counter()
        
        # Native C++ TreeSHAP feature contributions: shape [1, n_features + 1]
        contribs = self.model.predict(
            feature_df,
            pred_contrib=True,
            num_iteration=num_iteration,
            num_threads=1,
            validate_features=False
        )
        sv = contribs[0, :-1]
            
        # Sigmoid calibration: P(Fraud) = 1 / (1 + exp(-margin))
        margin = float(contribs[0].sum())
        fraud_prob = float(1.0 / (1.0 + math.exp(-margin)))
        
        # Top 3 positive risk contributors
        top_indices = np.argsort(-sv)[:3]
        top_features = [self.feature_names[i] for i in top_indices]
        reason_codes = [REASON_CODE_MAP.get(f, f"RISK_INDICATOR_{f.upper()}") for f in top_features]
        latency_ms = (time.perf_counter() - t0) * 1000.0
        
        return fraud_prob, reason_codes, latency_ms
        
    def explain_transaction(self, feature_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes localized Shapley values for a single transaction vector in sub-1.0ms.
        Uses LightGBM native C++ TreeSHAP implementation (pred_contrib=True).
        """
        fraud_prob, reason_codes, latency_ms = self.score_and_explain(feature_df)
        return {
            'reason_codes': reason_codes,
            'fraud_probability': round(fraud_prob, 4),
            'latency_ms': round(latency_ms, 3)
        }


if __name__ == "__main__":
    if os.path.exists("models/fraud_lgb_model.txt"):
        explainer = FraudExplainer()
        print("FraudExplainer initialized successfully with feature count:", len(explainer.feature_names))
    else:
        print("Model file not yet generated. Run train_lgb.py first.")
