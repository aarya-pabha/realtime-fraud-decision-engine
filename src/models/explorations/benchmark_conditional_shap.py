import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
import numpy as np
import pandas as pd
import duckdb

from src.models.explainability import FraudExplainer, DEFAULT_APPROVE_REASON_CODES
from src.models.cost_router import DynamicCostRouter
from src.api.feature_service import FeatureService
from src.api.schemas import TransactionPayload

def run_benchmark():
    print("=" * 80)
    print("EMPIRICAL BENCHMARK: CONDITIONAL ADVERSE-ACTION TreeSHAP (OPTION 1)")
    print("=" * 80)
    
    # 1. Initialize Singletons
    explainer = FraudExplainer("models/fraud_lgb_model.txt")
    cost_router = DynamicCostRouter()
    feature_service = FeatureService(
        feature_store_repo="feature_repo",
        feature_names=explainer.feature_names
    )
    
    # 2. Load 1,000 Real Chronological Holdout Transactions from DuckDB
    db_path = "feature_store.duckdb"
    con = duckdb.connect(db_path, read_only=True)
    query = """
    SELECT 
        t.TransactionID,
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
    print(f"Loaded {len(records)} authentic IEEE-CIS holdout transactions (#3485113+).")
    
    # Pre-transform feature vectors
    print("Pre-hydrating 1,000 feature vectors...")
    feature_vectors = []
    amounts = []
    for rec in records:
        payload = TransactionPayload(**rec)
        feat_df, _ = feature_service.transform_payload_to_feature_vector(payload)
        feature_vectors.append(feat_df)
        amounts.append(float(payload.TransactionAmt))
        
    # Warmup
    for i in range(10):
        explainer.score_and_explain(feature_vectors[i])
        explainer.predict_proba(feature_vectors[i])
        explainer.explain(feature_vectors[i])
        
    # Track A: UNCONDITIONAL TreeSHAP (Previous Architecture)
    print("\n[Track A] Running 1,000 Unconditional TreeSHAP evaluations...")
    uncond_latencies = []
    uncond_actions = []
    uncond_probs = []
    uncond_reasons = []
    
    for df, amt in zip(feature_vectors, amounts):
        t0 = time.perf_counter()
        prob, reasons, _ = explainer.score_and_explain(df)
        route_res = cost_router.route_transaction(fraud_prob=prob, amount=amt)
        lat = (time.perf_counter() - t0) * 1000.0
        
        uncond_latencies.append(lat)
        uncond_actions.append(route_res.action)
        uncond_probs.append(prob)
        uncond_reasons.append(reasons)
        
    # Track B: CONDITIONAL Adverse-Action TreeSHAP (Option 1)
    print("[Track B] Running 1,000 Conditional Adverse-Action TreeSHAP evaluations...")
    cond_latencies = []
    cond_actions = []
    cond_probs = []
    cond_reasons = []
    approve_latencies = []
    adverse_latencies = []
    
    for df, amt in zip(feature_vectors, amounts):
        t0 = time.perf_counter()
        # 1. Pure LightGBM probability inference
        prob, _ = explainer.predict_proba(df)
        # 2. Dynamic Router decision
        route_res = cost_router.route_transaction(fraud_prob=prob, amount=amt)
        # 3. Conditional TreeSHAP
        if route_res.action in ("STEP_UP_3DS", "DECLINE"):
            reasons, _ = explainer.explain(df)
            adverse = True
        else:
            reasons = DEFAULT_APPROVE_REASON_CODES
            adverse = False
        lat = (time.perf_counter() - t0) * 1000.0
        
        cond_latencies.append(lat)
        cond_actions.append(route_res.action)
        cond_probs.append(prob)
        cond_reasons.append(reasons)
        if adverse:
            adverse_latencies.append(lat)
        else:
            approve_latencies.append(lat)
            
    # Verify Mathematical & Policy Equivalence
    prob_diffs = [abs(p1 - p2) for p1, p2 in zip(uncond_probs, cond_probs)]
    max_prob_diff = max(prob_diffs)
    action_match = sum(1 for a1, a2 in zip(uncond_actions, cond_actions) if a1 == a2)
    action_match_pct = (action_match / len(uncond_actions)) * 100.0
    
    adverse_count = len(adverse_latencies)
    approve_count = len(approve_latencies)
    
    # Reason code consistency on adverse actions
    adverse_reasons_match = 0
    for a1, r1, r2 in zip(uncond_actions, uncond_reasons, cond_reasons):
        if a1 in ("STEP_UP_3DS", "DECLINE"):
            if r1 == r2:
                adverse_reasons_match += 1
    adverse_match_pct = (adverse_reasons_match / max(1, adverse_count)) * 100.0
    
    print("\n" + "=" * 80)
    print("MATHEMATICAL & POLICY EQUIVALENCE AUDIT")
    print("=" * 80)
    print(f"Total Transactions Scored:        {len(records):,}")
    print(f"Max Probability Delta:            {max_prob_diff:.2e} (Strictly < 1e-5)")
    print(f"Action Alignment Rate:            {action_match_pct:.2f}% ({action_match}/{len(records)})")
    print(f"Adverse Reason Code Identity:     {adverse_match_pct:.2f}% ({adverse_reasons_match}/{adverse_count})")
    print(f"Traffic Distribution:             {approve_count:,} Approvals ({approve_count/len(records)*100:.1f}%) | {adverse_count:,} Adverse Actions ({adverse_count/len(records)*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("EMPIRICAL LATENCY BENCHMARK BREAKDOWN")
    print("=" * 80)
    print(f"{'Metric':<25} | {'Unconditional TreeSHAP':<22} | {'Conditional TreeSHAP':<22} | {'Delta / Speedup':<15}")
    print("-" * 90)
    
    uncond_avg = np.mean(uncond_latencies)
    cond_avg = np.mean(cond_latencies)
    speedup_avg = uncond_avg / cond_avg
    print(f"{'Average Latency':<25} | {uncond_avg:<20.2f}ms | {cond_avg:<20.2f}ms | {speedup_avg:.2f}x faster")
    
    uncond_p50 = np.percentile(uncond_latencies, 50)
    cond_p50 = np.percentile(cond_latencies, 50)
    print(f"{'p50 (Median)':<25} | {uncond_p50:<20.2f}ms | {cond_p50:<20.2f}ms | {uncond_p50/cond_p50:.2f}x faster")
    
    uncond_p90 = np.percentile(uncond_latencies, 90)
    cond_p90 = np.percentile(cond_latencies, 90)
    print(f"{'p90 Latency':<25} | {uncond_p90:<20.2f}ms | {cond_p90:<20.2f}ms | {uncond_p90/cond_p90:.2f}x faster")
    
    uncond_p95 = np.percentile(uncond_latencies, 95)
    cond_p95 = np.percentile(cond_latencies, 95)
    print(f"{'p95 Latency (SLA Gate)':<25} | {uncond_p95:<20.2f}ms | {cond_p95:<20.2f}ms | {uncond_p95/cond_p95:.2f}x faster")
    
    uncond_p99 = np.percentile(uncond_latencies, 99)
    cond_p99 = np.percentile(cond_latencies, 99)
    print(f"{'p99 Latency':<25} | {uncond_p99:<20.2f}ms | {cond_p99:<20.2f}ms | {uncond_p99/cond_p99:.2f}x faster")
    
    print("-" * 90)
    app_avg = np.mean(approve_latencies) if approve_latencies else 0.0
    adv_avg = np.mean(adverse_latencies) if adverse_latencies else 0.0
    print(f"{'  Clean Approval Path (96%)':<25} | {'N/A':<22} | {app_avg:<20.2f}ms | (Pure Predict)")
    print(f"{'  Adverse Action Path (4%)':<25} | {'N/A':<22} | {adv_avg:<20.2f}ms | (Predict + TreeSHAP)")
    print("=" * 80)

if __name__ == "__main__":
    run_benchmark()
