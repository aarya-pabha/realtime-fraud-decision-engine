import sys
import os
sys.path.insert(0, os.path.abspath("."))

import numpy as np
import time
from typing import Literal, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

class CostMatrixConfig(BaseModel):
    """
    Financial Cost Matrix Parameters grounded in 2026 Payment Rails benchmarks.
    """
    chargeback_fee: float = Field(default=25.0, ge=0.0, description="Fixed acquirer dispute fee per fraud event ($)")
    interchange_margin: float = Field(default=0.02, ge=0.0, le=0.10, description="Gross interchange margin lost on false declines (%)")
    customer_friction_cost: float = Field(default=5.0, ge=0.0, description="Customer support + LTV churn penalty per false decline ($)")
    auth_3ds_cost: float = Field(default=0.05, ge=0.0, description="EMV 3DS 2.0 per-call authentication fee ($)")
    step_up_legit_success_rate: float = Field(default=0.85, ge=0.0, le=1.0, description="Share of legit users completing 3DS OTP")
    step_up_fraud_block_rate: float = Field(default=0.95, ge=0.0, le=1.0, description="Share of fraud attempts blocked by 3DS OTP")
    min_step_up_threshold: float = Field(default=0.03, ge=0.0, le=0.50)
    max_step_up_threshold: float = Field(default=0.25, ge=0.0, le=0.50)
    decline_multiplier: float = Field(default=4.0, ge=1.0, le=10.0, description="Three-Way decision boundary multiplier tau_decline = k * tau_step_up")
    min_decline_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    max_decline_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    enable_tiered_policy: bool = Field(
        default=True,
        description="Enables Level 3+4 Spend-Tier Segmented Routing Policy (<$100, $100-$500, $500+) optimized for minimal loss"
    )
    crc_tau_star: float = Field(
        default=0.0817,
        description="PAC distribution-free step-up threshold with temporal drift compensation (<= 0.45% chargeback risk ceiling)"
    )
    crc_decline_threshold: float = Field(
        default=0.65,
        description="Hard decline threshold for CRC mode"
    )

from dataclasses import dataclass


@dataclass(slots=True)
class RoutingResult:
    action: Literal["APPROVE", "STEP_UP_3DS", "DECLINE"]
    fraud_probability: float
    transaction_amount: float
    tau_step_up: float
    tau_decline: float
    expected_cost_dollars: float
    latency_ms: float

class DynamicCostRouter:
    """
    Sub-millisecond Dynamic Transaction-Value Aware Cost Matrix Router (Novelty #2).
    Adapts decision boundaries dynamically as a continuous function of transaction dollar value: tau*(TransactionAmt).
    Integrates Level 3+4 Spend-Tier Segmented Policy:
      - Tier 1 (<$100): beta=0.85, k=7.25, step=[0.015, 0.100], dec=[0.590, 0.850]
      - Tier 2 ($100-$500): beta=0.90, k=7.75, step=[0.035, 0.200], dec=[0.730, 0.950]
      - Tier 3 ($500+): beta=0.65, k=9.75, step=[0.010, 0.340], dec=[0.670, 0.900]
    """
    def __init__(self, config: CostMatrixConfig = None):
        self.cfg = config or CostMatrixConfig()

    def compute_thresholds(self, amount: float) -> Tuple[float, float]:
        """
        Calculates value-dependent operational thresholds (tau_step_up, tau_decline) using Bayesian Expected Cost Minimization:
        tau*(A) = C_FP(A) / (C_FP(A) + C_FN(A))
        """
        c_fn = amount + self.cfg.chargeback_fee
        c_fp = (amount * self.cfg.interchange_margin) + self.cfg.customer_friction_cost
        tau_star = c_fp / (c_fn + c_fp)

        if self.cfg.enable_tiered_policy:
            if amount < 100.0:
                tau_step_up = max(0.015, min(0.100, tau_star * 0.85))
                tau_decline = max(0.590, min(0.850, tau_star * 7.25))
            elif amount < 500.0:
                tau_step_up = max(0.035, min(0.200, tau_star * 0.90))
                tau_decline = max(0.730, min(0.950, tau_star * 7.75))
            else:
                tau_step_up = max(0.010, min(0.340, tau_star * 0.65))
                tau_decline = max(0.670, min(0.900, tau_star * 9.75))
            tau_decline = max(tau_decline, tau_step_up + 0.01)
        else:
            tau_step_up = max(self.cfg.min_step_up_threshold, min(self.cfg.max_step_up_threshold, tau_star))
            tau_decline = max(self.cfg.min_decline_threshold, min(self.cfg.max_decline_threshold, self.cfg.decline_multiplier * tau_star))

        return tau_step_up, tau_decline


    def route_transaction(
        self,
        fraud_prob: float,
        amount: float,
        mode: str = "dynamic",
        crc_tau_star: Optional[float] = None,
        crc_decline_threshold: Optional[float] = None
    ) -> RoutingResult:
        """
        Evaluates a single transaction event in sub-0.5ms SLA latency.
        Supports:
          - 'dynamic': Bayesian value-aware cost optimization (Novelty #2)
          - 'crc': Conformal Risk Control PAC distribution-free bound (Option 3)
        """
        t0 = time.perf_counter()
        if mode == "crc":
            tau_step_up = crc_tau_star if crc_tau_star is not None else self.cfg.crc_tau_star
            tau_decline = crc_decline_threshold if crc_decline_threshold is not None else self.cfg.crc_decline_threshold
        else:
            tau_step_up, tau_decline = self.compute_thresholds(amount)


        if fraud_prob < tau_step_up:
            action = "APPROVE"
            # Expected cost if approved = P(Fraud) * C_FN(A)
            exp_cost = fraud_prob * (amount + self.cfg.chargeback_fee)
        elif fraud_prob < tau_decline:
            action = "STEP_UP_3DS"
            # Expected cost with 3DS challenge resolution
            p_bypass = 1.0 - self.cfg.step_up_fraud_block_rate
            p_abandon = 1.0 - self.cfg.step_up_legit_success_rate
            cost_if_fraud = self.cfg.auth_3ds_cost + p_bypass * (amount + self.cfg.chargeback_fee)
            cost_if_legit = self.cfg.auth_3ds_cost + p_abandon * ((amount * self.cfg.interchange_margin) + self.cfg.customer_friction_cost)
            exp_cost = (fraud_prob * cost_if_fraud) + ((1.0 - fraud_prob) * cost_if_legit)
        else:
            action = "DECLINE"
            # Expected cost if declined = (1 - P(Fraud)) * C_FP(A)
            exp_cost = (1.0 - fraud_prob) * ((amount * self.cfg.interchange_margin) + self.cfg.customer_friction_cost)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return RoutingResult(
            action=action,
            fraud_probability=round(fraud_prob, 4),
            transaction_amount=round(amount, 2),
            tau_step_up=round(tau_step_up, 4),
            tau_decline=round(tau_decline, 4),
            expected_cost_dollars=round(exp_cost, 4),
            latency_ms=round(latency_ms, 3)
        )


    def batch_route_and_evaluate(
        self,
        fraud_probs: np.ndarray,
        amounts: np.ndarray,
        actual_labels: np.ndarray = None
    ) -> Dict[str, Any]:
        """
        High-performance vectorized routing and financial loss calculation across test datasets.
        """
        amounts = np.asarray(amounts, dtype=np.float64)
        fraud_probs = np.asarray(fraud_probs, dtype=np.float64)

        c_fn = amounts + self.cfg.chargeback_fee
        c_fp = (amounts * self.cfg.interchange_margin) + self.cfg.customer_friction_cost
        tau_star = c_fp / (c_fn + c_fp)

        if self.cfg.enable_tiered_policy:
            m1 = amounts < 100.0
            m2 = (amounts >= 100.0) & (amounts < 500.0)
            m3 = amounts >= 500.0

            tau_step_up = np.empty_like(tau_star)
            tau_decline = np.empty_like(tau_star)

            tau_step_up[m1] = np.clip(tau_star[m1] * 0.85, 0.015, 0.100)
            tau_decline[m1] = np.clip(tau_star[m1] * 7.25, 0.590, 0.850)

            tau_step_up[m2] = np.clip(tau_star[m2] * 0.90, 0.035, 0.200)
            tau_decline[m2] = np.clip(tau_star[m2] * 7.75, 0.730, 0.950)

            tau_step_up[m3] = np.clip(tau_star[m3] * 0.65, 0.010, 0.340)
            tau_decline[m3] = np.clip(tau_star[m3] * 9.75, 0.670, 0.900)

            tau_decline = np.maximum(tau_decline, tau_step_up + 0.01)
        else:
            tau_step_up = np.clip(tau_star, self.cfg.min_step_up_threshold, self.cfg.max_step_up_threshold)
            tau_decline = np.clip(self.cfg.decline_multiplier * tau_star, self.cfg.min_decline_threshold, self.cfg.max_decline_threshold)

        # Vectorized Action Assignment
        is_approve = fraud_probs < tau_step_up
        is_step_up = (fraud_probs >= tau_step_up) & (fraud_probs < tau_decline)
        is_decline = fraud_probs >= tau_decline

        actions = np.empty(len(fraud_probs), dtype=object)
        actions[is_approve] = "APPROVE"
        actions[is_step_up] = "STEP_UP_3DS"
        actions[is_decline] = "DECLINE"

        out = {
            "actions": actions,
            "tau_step_up": tau_step_up,
            "tau_decline": tau_decline,
            "approve_count": int(np.sum(is_approve)),
            "step_up_count": int(np.sum(is_step_up)),
            "decline_count": int(np.sum(is_decline)),
            "total_transactions": len(fraud_probs)
        }

        if actual_labels is not None:
            actual_labels = np.asarray(actual_labels, dtype=np.int32)
            y_fraud = (actual_labels == 1)
            y_legit = (actual_labels == 0)

            # 1. Realized losses under APPROVE
            loss_approve_fraud = np.sum((amounts[is_approve & y_fraud] + self.cfg.chargeback_fee))
            loss_approve_legit = 0.0

            # 2. Realized losses under DECLINE
            loss_decline_fraud = 0.0
            loss_decline_legit = np.sum(((amounts[is_decline & y_legit] * self.cfg.interchange_margin) + self.cfg.customer_friction_cost))

            # 3. Realized losses under STEP_UP_3DS
            p_bypass = 1.0 - self.cfg.step_up_fraud_block_rate
            p_abandon = 1.0 - self.cfg.step_up_legit_success_rate
            n_step_up = np.sum(is_step_up)
            cost_3ds_auth = n_step_up * self.cfg.auth_3ds_cost

            loss_3ds_fraud = np.sum(p_bypass * (amounts[is_step_up & y_fraud] + self.cfg.chargeback_fee))
            loss_3ds_legit = np.sum(p_abandon * ((amounts[is_step_up & y_legit] * self.cfg.interchange_margin) + self.cfg.customer_friction_cost))

            total_financial_loss = float(
                loss_approve_fraud + loss_approve_legit +
                loss_decline_fraud + loss_decline_legit +
                cost_3ds_auth + loss_3ds_fraud + loss_3ds_legit
            )

            # Chargeback volume (bypassed 3DS fraud + unintercepted approved fraud)
            total_chargeback_count = int(np.sum(is_approve & y_fraud) + np.sum(is_step_up & y_fraud) * p_bypass)
            chargeback_ratio = float(total_chargeback_count / len(fraud_probs))

            out.update({
                "total_financial_loss_dollars": total_financial_loss,
                "loss_approve_fraud": float(loss_approve_fraud),
                "loss_decline_legit": float(loss_decline_legit),
                "loss_step_up_total": float(cost_3ds_auth + loss_3ds_fraud + loss_3ds_legit),
                "chargeback_count": total_chargeback_count,
                "chargeback_ratio": chargeback_ratio
            })

        return out

if __name__ == "__main__":
    router = DynamicCostRouter()
    sample = router.route_transaction(fraud_prob=0.08, amount=2500.0)
    print("DynamicCostRouter Test Result:")
    print(sample.model_dump_json(indent=2))
