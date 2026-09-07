import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import json
import duckdb
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

from src.models.explainability import FraudExplainer, DEFAULT_APPROVE_REASON_CODES
from src.models.cost_router import DynamicCostRouter, RoutingResult
from src.api.feature_service import FeatureService
from src.api.schemas import TransactionPayload
from sklearn.metrics import roc_auc_score, average_precision_score

def run_stress_test_suite():
    print("=" * 95)
    print("INDEPENDENT EMPIRICAL STRESS TEST & BENCHMARK: ALL 3 NOVELTY OPTIONS")
    print("=" * 95)
    
    # 1. Load 1,000 authentic chronological holdout transactions from DuckDB
    db_path = "feature_store.duckdb"
    con = duckdb.connect(db_path, read_only=True)
    query = """
    SELECT 
        t.TransactionID,
        t.isFraud,
        t.TransactionDT,
        t.TransactionAmt,
        t.ProductCD,
        t.card1, t.card2, t.card3, t.card4, t.card5, t.card6,
        t.addr1, t.addr2,
        t.P_emaildomain, t.R_emaildomain,
        t.D1, t.D2, t.D15,
        t.C1, t.C2, t.C3, t.C4, t.C5, t.C6, t.C7, t.C8, t.C9, t.C10, t.C11, t.C12, t.C13, t.C14,
        i.DeviceType, i.DeviceInfo, i.id_30, i.id_31, i.id_33
    FROM transactions t
    LEFT JOIN identities i ON t.TransactionID = i.TransactionID
    WHERE t.TransactionDT >= 13046400
    ORDER BY t.TransactionDT ASC
    LIMIT 1000;
    """
    records = con.execute(query).to_arrow_table().to_pylist()
    con.close()
    
    y_true = np.array([r["isFraud"] for r in records], dtype=np.int32)
    amounts = np.array([float(r["TransactionAmt"]) for r in records], dtype=np.float64)
    print(f"Loaded {len(records):,} authentic holdout transactions (Fraud: {np.sum(y_true):,}, {np.mean(y_true)*100:.2f}%).")
    
    # 2. Initialize Models & Engines
    print("Initializing engine singletons...")
    base_model_path = "models/fraud_lgb_model.txt"
    decay_model_path = "models/fraud_lgb_temporal_decay_90d.txt"
    
    base_explainer = FraudExplainer(base_model_path)
    decay_explainer = FraudExplainer(decay_model_path)
    cost_router = DynamicCostRouter()
    
    feature_service = FeatureService(
        feature_store_repo="feature_repo",
        feature_names=base_explainer.feature_names
    )
    
    print("Pre-hydrating 1,000 feature vectors...")
    feature_vectors = []
    for rec in records:
        payload = TransactionPayload(**rec)
        feat_df, _ = feature_service.transform_payload_to_feature_vector(payload)
        feature_vectors.append(feat_df)

    # 3. Define 4 Independent Configurations to Stress Test
    # Each configuration isolates EXACTLY one architectural novelty
    configs = [
        {
            "name": "0. Baseline (Production Master)",
            "desc": "Uniform Model + Unconditional TreeSHAP + Level 3+4 Router",
            "explainer": base_explainer,
            "conditional_shap": False,
            "routing_mode": "dynamic",
            "crc_tau": None
        },
        {
            "name": "1. Option 1 (Conditional TreeSHAP)",
            "desc": "Uniform Model + Conditional TreeSHAP + Level 3+4 Router",
            "explainer": base_explainer,
            "conditional_shap": True,
            "routing_mode": "dynamic",
            "crc_tau": None
        },
        {
            "name": "2. Option 2 (Temporal Decay 90d)",
            "desc": "90-Day Decay Model + Conditional TreeSHAP + Level 3+4 Router",
            "explainer": decay_explainer,
            "conditional_shap": True,
            "routing_mode": "dynamic",
            "crc_tau": None
        },
        {
            "name": "3. Option 3 (Conformal Risk Control)",
            "desc": "Uniform Model + Conditional TreeSHAP + CRC Bound (alpha=0.45%)",
            "explainer": base_explainer,
            "conditional_shap": True,
            "routing_mode": "crc",
            "crc_tau": 0.0817
        }
    ]

    benchmark_results = []
    CONCURRENCY = 50

    for cfg in configs:
        print(f"\n[Stress Testing] {cfg['name']} under {CONCURRENCY} concurrent workers...")
        explainer = cfg["explainer"]
        cond_shap = cfg["conditional_shap"]
        routing_mode = cfg["routing_mode"]
        crc_tau = cfg["crc_tau"]
        
        # Warmup
        for i in range(10):
            explainer.predict_proba(feature_vectors[i])
            if not cond_shap:
                explainer.score_and_explain(feature_vectors[i])
            else:
                explainer.explain(feature_vectors[i])

        def score_single_tx(idx: int):
            df = feature_vectors[idx]
            amt = amounts[idx]
            t0 = time.perf_counter()
            
            if not cond_shap:
                prob, reasons, _ = explainer.score_and_explain(df)
            else:
                prob, _ = explainer.predict_proba(df)
                
            if routing_mode == "crc":
                if prob < crc_tau:
                    action = "APPROVE"
                elif prob < 0.65:
                    action = "STEP_UP_3DS"
                else:
                    action = "DECLINE"
            else:
                r_res = cost_router.route_transaction(fraud_prob=prob, amount=amt)
                action = r_res.action
                
            if cond_shap:
                if action in ("STEP_UP_3DS", "DECLINE"):
                    reasons, _ = explainer.explain(df)
                else:
                    reasons = DEFAULT_APPROVE_REASON_CODES
                    
            lat = (time.perf_counter() - t0) * 1000.0
            return idx, prob, action, lat, reasons

        # Launch concurrent stress execution
        t_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            raw_results = list(executor.map(score_single_tx, range(len(records))))
        total_time_sec = time.perf_counter() - t_start
        
        # Sort back to chronological order
        raw_results.sort(key=lambda x: x[0])
        probs = np.array([r[1] for r in raw_results])
        actions = [r[2] for r in raw_results]
        latencies = np.array([r[3] for r in raw_results])
        
        # 1. Compute Performance Metrics
        rps = len(records) / total_time_sec
        avg_lat = np.mean(latencies)
        p50 = np.percentile(latencies, 50)
        p90 = np.percentile(latencies, 90)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        max_lat = np.max(latencies)
        
        # 2. Compute Quality / Ranking Metrics
        roc = roc_auc_score(y_true, probs)
        pr = average_precision_score(y_true, probs)
        
        # 3. Compute Financial Loss and Policy Distribution
        approvals = sum(1 for a in actions if a == "APPROVE")
        step_ups = sum(1 for a in actions if a == "STEP_UP_3DS")
        declines = sum(1 for a in actions if a == "DECLINE")
        
        # Financial loss formula on the 1,000 cohort
        loss_app = sum(amt + 25.0 for a, amt, y in zip(actions, amounts, y_true) if a == "APPROVE" and y == 1)
        loss_dec = sum((amt * 0.02) + 5.0 for a, amt, y in zip(actions, amounts, y_true) if a == "DECLINE" and y == 0)
        loss_3ds = (step_ups * 0.05) + \
                   sum(0.05 * (amt + 25.0) for a, amt, y in zip(actions, amounts, y_true) if a == "STEP_UP_3DS" and y == 1) + \
                   sum(0.15 * ((amt * 0.02) + 5.0) for a, amt, y in zip(actions, amounts, y_true) if a == "STEP_UP_3DS" and y == 0)
        total_loss = loss_app + loss_dec + loss_3ds
        
        # Realized Chargeback Ratio (unblocked fraud / approved traffic)
        cb_count = sum(1 for a, y in zip(actions, y_true) if a == "APPROVE" and y == 1) + \
                   0.05 * sum(1 for a, y in zip(actions, y_true) if a == "STEP_UP_3DS" and y == 1)
        cb_ratio = (cb_count / max(1, approvals)) * 100.0
        
        res = {
            "name": cfg["name"],
            "desc": cfg["desc"],
            "rps": rps,
            "avg_lat": avg_lat,
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "p99": p99,
            "max_lat": max_lat,
            "roc": roc,
            "pr": pr,
            "approvals_pct": (approvals / len(records)) * 100.0,
            "step_ups_pct": (step_ups / len(records)) * 100.0,
            "declines_pct": (declines / len(records)) * 100.0,
            "total_loss": total_loss,
            "cb_ratio": cb_ratio
        }
        benchmark_results.append(res)

    # 4. Print Beautiful Side-by-Side Comparison Tables
    print("\n" + "=" * 115)
    print("INDEPENDENT STRESS TEST LATENCY & THROUGHPUT BREAKDOWN (50 CONCURRENT WORKERS)")
    print("=" * 115)
    print(f"{'Configuration':<35} | {'Throughput':<12} | {'p50 (Med)':<11} | {'p90':<9} | {'p95':<9} | {'p99':<9} | {'Avg Lat':<10}")
    print("-" * 115)
    for b in benchmark_results:
        print(f"{b['name']:<35} | {b['rps']:<10.1f}/s | {b['p50']:<8.2f} ms | {b['p90']:<6.2f} ms | {b['p95']:<6.2f} ms | {b['p99']:<6.2f} ms | {b['avg_lat']:<7.2f} ms")
    print("=" * 115)
    
    print("\n" + "=" * 115)
    print("INDEPENDENT BUSINESS, FINANCIAL & POLICY VERIFICATION MATRIX")
    print("=" * 115)
    print(f"{'Configuration':<35} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'Approve%':<9} | {'3DS%':<7} | {'Decline%':<9} | {'Loss (1k cohort)':<16} | {'CB Ratio':<8}")
    print("-" * 115)
    for b in benchmark_results:
        print(f"{b['name']:<35} | {b['pr']:<8.4f} | {b['roc']:<8.4f} | {b['approvals_pct']:<7.1f}% | {b['step_ups_pct']:<5.1f}% | {b['declines_pct']:<7.1f}% | ${b['total_loss']:<15,.2f} | {b['cb_ratio']:<7.2f}%")
    print("=" * 115)

if __name__ == "__main__":
    run_stress_test_suite()
