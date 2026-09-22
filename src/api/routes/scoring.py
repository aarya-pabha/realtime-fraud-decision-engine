import os
import time
from typing import Annotated
from fastapi import APIRouter, Depends, status

from src.api.schemas import TransactionPayload, ScoringResponse, LatencyBreakdown, ThresholdsInfo
from src.api.dependencies import ScoringEngineContainer, get_scoring_engine
from src.models.explainability import DEFAULT_APPROVE_REASON_CODES

router = APIRouter(prefix="/v1", tags=["Real-Time Scoring"])


@router.post("/score", response_model=ScoringResponse, status_code=status.HTTP_200_OK)
async def score_transaction(
    payload: TransactionPayload,
    engine: Annotated[ScoringEngineContainer, Depends(get_scoring_engine)]
):
    """
    Real-Time Transaction Scoring & Bayesian Dynamic Cost Decisioning Endpoint.
    Executed as an async coroutine directly in the event loop for ultra-low-latency in-memory compute.
    Supports dynamic evaluation across:
      - Baseline: Unconditional TreeSHAP (ENABLE_CONDITIONAL_SHAP=0)
      - Option 1: Conditional Adverse-Action TreeSHAP (ENABLE_CONDITIONAL_SHAP=1)
      - Option 2: 90-Day Temporal Decay Model (via MODEL_PATH)
      - Option 3: Conformal Risk Control PAC Bound Routing (ROUTING_MODE=crc)
    """
    total_start = time.perf_counter()
    
    # 1. Online Feature Hydration & Real-Time Transformation
    feature_df, hydration_ms = engine.feature_service.transform_payload_to_feature_vector(payload)
    
    # 2. Pure LightGBM Probability Inference (<3.5ms)
    fraud_prob, inference_ms = engine.explainer.predict_proba(feature_df)
    
    # 3. Decision Routing (Bayesian Value-Adaptive Cost Router by default)
    t_route = time.perf_counter()
    routing_mode = os.environ.get("ROUTING_MODE", "dynamic")
    crc_tau_star = float(os.environ.get("CRC_TAU_STAR", "0.0817"))
    routing_result = engine.cost_router.route_transaction(
        fraud_prob=fraud_prob,
        amount=float(payload.TransactionAmt),
        mode=routing_mode,
        crc_tau_star=crc_tau_star
    )
    routing_ms = (time.perf_counter() - t_route) * 1000.0

    
    # 4. TreeSHAP Attribution (Conditional vs Unconditional)
    enable_cond_shap = os.environ.get("ENABLE_CONDITIONAL_SHAP", "1") != "0"
    if not enable_cond_shap or routing_result.action in ("STEP_UP_3DS", "DECLINE"):
        reason_codes, shap_ms = engine.explainer.explain(feature_df)
    else:
        reason_codes = DEFAULT_APPROVE_REASON_CODES
        shap_ms = 0.0

    
    total_latency_ms = (time.perf_counter() - total_start) * 1000.0
    
    tx_id = payload.TransactionID or int(time.time() * 1000) % 10000000
    
    return ScoringResponse(
        transaction_id=tx_id,
        action=routing_result.action,
        fraud_probability=round(fraud_prob, 4),
        transaction_amount=round(float(payload.TransactionAmt), 2),
        expected_cost_dollars=round(routing_result.expected_cost_dollars, 4),
        reason_codes=reason_codes,
        thresholds=ThresholdsInfo(
            tau_step_up=routing_result.tau_step_up,
            tau_decline=routing_result.tau_decline
        ),
        latency=LatencyBreakdown(
            feature_hydration_ms=round(hydration_ms, 3),
            model_inference_ms=round(inference_ms, 3),
            shap_explain_ms=round(shap_ms, 3),
            dynamic_routing_ms=round(routing_ms, 3),
            total_latency_ms=round(total_latency_ms, 3)
        )
    )
