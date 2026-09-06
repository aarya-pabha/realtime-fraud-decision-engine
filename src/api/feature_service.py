import time
import os
import re
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from src.models.dataset_loader import (
    V_MEDOID_COLS,
    parse_device_corp,
    parse_browser_corp,
    parse_os_family,
    parse_screen_ratio
)
from src.api.schemas import TransactionPayload

DISPOSABLE_DOMAINS = frozenset({'mailinator.com', 'guerrillamail.com', 'tempmail.com', '10minutemail.com', 'throwawaymail.com'})
V_MEDOID_DEFAULTS = {v: [0.0] for v in V_MEDOID_COLS}

class FeatureService:
    """
    Sub-5ms Online Feature Hydration & Real-Time Transformation Service.
    Retrieves rolling velocity counters from Feast Redis online store and computes on-the-fly streaming transforms.
    """
    def __init__(self, feature_store_repo: str = "feature_repo", feature_names: list = None):
        self.feature_store = None
        self.feature_names = feature_names
        self.redis_online = False
        
        # Check if Redis online store is reachable (0.1s socket timeout)
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        os.environ.setdefault("REDIS_CONNECTION_STRING", f"{redis_host}:{redis_port}")
        
        try:
            import redis
            r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=0.1, socket_timeout=0.1)
            r.ping()
            self.redis_online = True
            print(f"[FeatureService] Redis online store connected at {redis_host}:{redis_port}.")
        except Exception:
            self.redis_online = False
            print("[FeatureService] Redis offline/unreachable. Operating with high-speed local feature fallback.")
        
        # Initialize Feast FeatureStore if repo exists and Redis is active
        if self.redis_online and os.path.exists(feature_store_repo):
            try:
                from feast import FeatureStore
                self.feature_store = FeatureStore(repo_path=feature_store_repo)
            except Exception as e:
                print(f"[FeatureService] Feast FeatureStore init skipped: {e}")
                self.feature_store = None
                
        # Baseline reference entity frequencies for cold-start imputation
        self.default_freqs = {
            'card_base_id_freq': 0.0001,
            'cardholder_uid_freq': 0.00005,
            'addr1_freq': 0.045,
            'P_emaildomain_freq': 0.380
        }
        
    @staticmethod
    def _to_int(val, default: int = 0) -> int:
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def build_entity_keys(self, payload: TransactionPayload) -> Tuple[str, str]:
        """Constructs dual-tier entity keys matching Feast store."""
        c1 = self._to_int(payload.card1)
        c2 = self._to_int(payload.card2)
        c3 = self._to_int(payload.card3)
        c4 = str(payload.card4 or 'unk').lower()
        c5 = self._to_int(payload.card5)
        c6 = str(payload.card6 or 'unk').lower()
        
        card_base_id = f"{c1}_{c2}_{c3}_{c4}_{c5}_{c6}"
        
        tx_id = payload.TransactionID or int(time.time() * 1000) % 10000000
        addr_str = str(self._to_int(payload.addr1)) if payload.addr1 is not None and not (isinstance(payload.addr1, float) and math.isnan(payload.addr1)) else f"NONE_{tx_id}"
        email_str = str(payload.P_emaildomain) if payload.P_emaildomain else f"NONE_{tx_id}"
        cardholder_uid = f"{card_base_id}_{addr_str}_{email_str}"
        
        return card_base_id, cardholder_uid

    def hydrate_online_features(self, card_base_id: str, payload: TransactionPayload) -> Tuple[Dict[str, Any], float]:
        """
        Queries Feast Redis online store for sub-5ms velocity features.
        Falls back to payload overrides or safe defaults if Redis is offline.
        """
        t0 = time.perf_counter()
        
        # Check for explicit manual overrides (e.g. from testing/benchmarking payload)
        if payload.tx_count_5m is not None and payload.tx_count_1h is not None and payload.amt_sum_24h is not None:
            hydration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "tx_count_5m": payload.tx_count_5m,
                "tx_count_1h": payload.tx_count_1h,
                "amt_sum_24h": payload.amt_sum_24h
            }, hydration_ms

        velocity_features = {
            "tx_count_5m": 0,
            "tx_count_1h": 1,
            "amt_sum_24h": float(payload.TransactionAmt)
        }
        
        if self.feature_store is not None:
            try:
                feature_response = self.feature_store.get_online_features(
                    features=[
                        "card_velocity_features:tx_count_5m",
                        "card_velocity_features:tx_count_1h",
                        "card_velocity_features:amt_sum_24h"
                    ],
                    entity_rows=[{"card_base_id": card_base_id}]
                ).to_dict()
                
                if feature_response and "tx_count_5m" in feature_response:
                    v_5m = feature_response["tx_count_5m"][0]
                    v_1h = feature_response["tx_count_1h"][0]
                    v_24h = feature_response["amt_sum_24h"][0]
                    
                    if v_5m is not None:
                        velocity_features["tx_count_5m"] = int(v_5m)
                    if v_1h is not None:
                        velocity_features["tx_count_1h"] = int(v_1h)
                    if v_24h is not None:
                        velocity_features["amt_sum_24h"] = float(v_24h)
            except Exception:
                # Safe fallback to local baseline defaults
                pass
                
        hydration_ms = (time.perf_counter() - t0) * 1000.0
        return velocity_features, hydration_ms

    def transform_payload_to_feature_vector(self, payload: TransactionPayload) -> Tuple[pd.DataFrame, float]:
        """
        Transforms raw TransactionPayload into 1-row DataFrame aligned with LightGBM Booster schema.
        """
        card_base_id, cardholder_uid = self.build_entity_keys(payload)
        velocity, hydration_ms = self.hydrate_online_features(card_base_id, payload)
        
        amt = float(payload.TransactionAmt)
        dt = int(payload.TransactionDT)
        
        # Currency and decimal volatility
        amt_str = str(amt)
        dec_places = len(amt_str.split('.')[1]) if '.' in amt_str else 0
        is_foreign = 1 if dec_places >= 3 else 0
        
        # Email consistency
        p_email = str(payload.P_emaildomain).lower() if payload.P_emaildomain else "missing"
        r_email = str(payload.R_emaildomain).lower() if payload.R_emaildomain else "missing"
        email_match = 1 if (p_email != "missing" and r_email != "missing" and p_email == r_email) else 0
        is_disposable = 1 if p_email in DISPOSABLE_DOMAINS else 0
        
        # Spend ratios & D-deltas
        amt_to_mean = amt / 135.0 # Population baseline mean
        amt_to_std = amt / 230.0  # Population baseline std
        d1 = float(payload.D1 or 0.0)
        d2 = float(payload.D2 or 0.0)
        d15 = float(payload.D15 or 0.0)
        v_overrides = payload.v_medoids
        
        # Direct single-pass ordered dictionary matching booster feature_names exactly
        data = {
            # Base numerical features
            'TransactionAmt': [amt],
            'log_TransactionAmt': [math.log1p(amt)],
            'amt_to_mean_card': [amt_to_mean],
            'amt_to_std_card': [amt_to_std],
            'is_foreign_currency': [is_foreign],
            'decimal_places': [dec_places],
            'hour_dt': [(dt // 3600) % 24],
            'day_dt': [(dt // (3600 * 24)) % 7],
            'email_domain_match': [email_match],
            'is_disposable_email': [is_disposable],
            'card_base_id_freq': [self.default_freqs['card_base_id_freq']],
            'cardholder_uid_freq': [self.default_freqs['cardholder_uid_freq']],
            'addr1_freq': [self.default_freqs['addr1_freq']],
            'P_emaildomain_freq': [self.default_freqs['P_emaildomain_freq']],
            'screen_aspect_ratio': [parse_screen_ratio(payload.id_33)],
            'tx_count_5m': [velocity['tx_count_5m']],
            'tx_count_1h': [velocity['tx_count_1h']],
            'amt_sum_24h': [velocity['amt_sum_24h']],
            
            # Scaled D-deltas
            'D1_to_mean_card': [d1 / 100.0],
            'D2_to_mean_card': [d2 / 100.0],
            'D15_to_mean_card': [d15 / 150.0],
            
            # C-Counters
            'C1': [float(payload.C1 or 0.0)],
            'C2': [float(payload.C2 or 0.0)],
            'C3': [float(payload.C3 or 0.0)],
            'C4': [float(payload.C4 or 0.0)],
            'C5': [float(payload.C5 or 0.0)],
            'C6': [float(payload.C6 or 0.0)],
            'C7': [float(payload.C7 or 0.0)],
            'C8': [float(payload.C8 or 0.0)],
            'C9': [float(payload.C9 or 0.0)],
            'C10': [float(payload.C10 or 0.0)],
            'C11': [float(payload.C11 or 0.0)],
            'C12': [float(payload.C12 or 0.0)],
            'C13': [float(payload.C13 or 0.0)],
            'C14': [float(payload.C14 or 0.0)],
        }
        
        # 33 V-Medoids in exact booster sequence
        if v_overrides:
            for v in V_MEDOID_COLS:
                data[v] = [float(v_overrides.get(v, 0.0))]
        else:
            data.update(V_MEDOID_DEFAULTS)
            
        # Categoricals instantiated directly with pd.Categorical
        data['ProductCD'] = pd.Categorical([str(payload.ProductCD or 'W')])
        data['card4'] = pd.Categorical([str(payload.card4 or 'visa').lower()])
        data['card6'] = pd.Categorical([str(payload.card6 or 'debit').lower()])
        data['P_emaildomain'] = pd.Categorical([p_email])
        data['R_emaildomain'] = pd.Categorical([r_email])
        data['device_corp'] = pd.Categorical([parse_device_corp(payload.DeviceInfo or payload.DeviceType)])
        data['browser_corp'] = pd.Categorical([parse_browser_corp(payload.id_31)])
        data['os_family'] = pd.Categorical([parse_os_family(payload.id_30)])
        
        return pd.DataFrame(data), hydration_ms
