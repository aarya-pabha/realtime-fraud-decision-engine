import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from src.models.cost_router import DynamicCostRouter, CostMatrixConfig, RoutingResult

def test_monotonicity_with_amount():
    """
    Asserts mathematical monotonicity: tau*(A) strictly decreases as transaction amount increases.
    """
    router = DynamicCostRouter()
    amounts = [5.0, 25.0, 100.0, 500.0, 2500.0, 10000.0]
    
    # Calculate unclipped theoretical thresholds
    cfg = router.cfg
    tau_stars = [
        ((a * cfg.interchange_margin) + cfg.customer_friction_cost) /
        ((a + cfg.chargeback_fee) + (a * cfg.interchange_margin) + cfg.customer_friction_cost)
        for a in amounts
    ]
    
    for i in range(len(tau_stars) - 1):
        assert tau_stars[i] > tau_stars[i+1], f"Monotonicity violated: tau*({amounts[i]}) = {tau_stars[i]:.4f} <= tau*({amounts[i+1]}) = {tau_stars[i+1]:.4f}"

def test_threshold_bounds_and_clamping():
    """
    Asserts operational threshold bounds [min_step, max_step] and [min_dec, max_dec] across extreme spend regimes.
    """
    router = DynamicCostRouter()
    extreme_amounts = [0.01, 1.0, 50.0, 500.0, 5000.0, 50000.0, 1000000.0]
    
    for amt in extreme_amounts:
        tau_step, tau_dec = router.compute_thresholds(amt)
        assert router.cfg.min_step_up_threshold <= tau_step <= router.cfg.max_step_up_threshold, f"tau_step out of bounds for amount {amt}: {tau_step}"
        assert router.cfg.min_decline_threshold <= tau_dec <= router.cfg.max_decline_threshold, f"tau_dec out of bounds for amount {amt}: {tau_dec}"
        assert tau_step < tau_dec, f"tau_step {tau_step} >= tau_decline {tau_dec} for amount {amt}"

def test_micro_vs_high_value_routing_behavior():
    """
    Asserts value-aware dynamic behavior:
    The exact same risk score (e.g. 10% fraud prob) is APPROVED for small coffee purchases ($10)
    but challenged with 3DS for high-value purchases ($3,000).
    """
    router = DynamicCostRouter()
    
    res_micro = router.route_transaction(fraud_prob=0.10, amount=10.0)
    assert res_micro.action == "APPROVE", f"Expected APPROVE for $10 with 10% risk, got {res_micro.action}"
    
    res_high = router.route_transaction(fraud_prob=0.10, amount=3000.0)
    assert res_high.action == "STEP_UP_3DS", f"Expected STEP_UP_3DS for $3000 with 10% risk, got {res_high.action}"
    
    res_extreme_fraud = router.route_transaction(fraud_prob=0.85, amount=150.0)
    assert res_extreme_fraud.action == "DECLINE", f"Expected DECLINE for 85% risk, got {res_extreme_fraud.action}"

def test_sub_millisecond_routing_latency():
    """
    Asserts single transaction decisioning runs well under the 1.0ms SLA requirement.
    """
    router = DynamicCostRouter()
    res = router.route_transaction(fraud_prob=0.04, amount=250.0)
    assert isinstance(res, RoutingResult)
    assert res.latency_ms < 1.0, f"Latency SLA exceeded: {res.latency_ms:.3f}ms"

def test_dynamic_router_financial_superiority():
    """
    Vectorized test verifying that Dynamic Cost Router achieves strictly lower financial loss than static 0.50 cutoff.
    """
    router = DynamicCostRouter()
    
    # Synthetic cohort: high value fraud (p=0.40, amt=$2000, y=1) and low value legit (p=0.40, amt=$20, y=0)
    amounts = np.array([2000.0, 20.0, 1500.0, 50.0, 3000.0])
    probs = np.array([0.40, 0.40, 0.35, 0.15, 0.45])
    labels = np.array([1, 0, 1, 0, 1])
    
    # Dynamic Router Evaluation
    dyn_res = router.batch_route_and_evaluate(probs, amounts, labels)
    
    # Static 0.50 Baseline (All 5 predicted legit -> missed 3 frauds)
    static_missed_fraud_loss = np.sum(amounts[labels == 1] + router.cfg.chargeback_fee)
    
    assert dyn_res["total_financial_loss_dollars"] < static_missed_fraud_loss, "Dynamic router did not outperform static baseline!"
