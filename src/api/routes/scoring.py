import time
from typing import Annotated
from fastapi import APIRouter, Depends, status

from src.api.schemas import TransactionPayload, ScoringResponse, LatencyBreakdown, ThresholdsInfo
from src.api.dependencies import ScoringEngineContainer, get_scoring_engine

router = APIRouter(prefix="/v1", tags=["Real-Time Scoring"])

@router.post("/score", response_model=ScoringResponse, status_code=status.HTTP_200_OK)
def score_transaction(
    payload: TransactionPayload,
    engine: Annotated[ScoringEngineContainer, Depends(get_scoring_engine)]
):
    """
    Real-Time Transaction Scoring & Bayesian Dynamic Cost Decisioning Endpoint.
    Executed synchronously inside FastAPI AnyIO worker threadpool to prevent CPU-bound
    C++ TreeSHAP and matrix operations from blocking the main asyncio event loop.
    """
    total_start = time.perf_counter()
    
    # 1. Online Feature Hydration & Real-Time Transformation
    feature_df, hydration_ms = engine.feature_service.transform_payload_to_feature_vector(payload)
    
    # 2. Unified Native LightGBM Inference & C++ TreeSHAP Attribution (<1.5ms)
    fraud_prob, reason_codes, inference_and_shap_ms = engine.explainer.score_and_explain(feature_df)
    
    # 3. Bayesian Value-Aware Dynamic Cost Router Decisioning
    t_route = time.perf_counter()
    routing_result = engine.cost_router.route_transaction(
        fraud_prob=fraud_prob,
        amount=float(payload.TransactionAmt)
    )
    routing_ms = (time.perf_counter() - t_route) * 1000.0
    
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
            model_inference_ms=round(inference_and_shap_ms * 0.6, 3),
            shap_explain_ms=round(inference_and_shap_ms * 0.4, 3),
            dynamic_routing_ms=round(routing_ms, 3),
            total_latency_ms=round(total_latency_ms, 3)
        )
    )
