import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, status

from src.api.schemas import HealthResponse

router = APIRouter(tags=["System Health & Metadata"])

@router.get("/", status_code=status.HTTP_200_OK)
def root_index() -> Dict[str, Any]:
    """Root metadata endpoint returning service catalog and documentation links."""
    return {
        "service": "Real-Time Transaction Fraud Detection Engine",
        "api_version": "v1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "scoring": "POST /v1/score",
            "feedback": "POST /v1/feedback",
            "feedback_stats": "GET /v1/feedback/stats",
            "health": "GET /v1/health"
        }
    }

@router.get("/v1/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def health_check(request: Request):
    """Liveness & readiness probe for Kubernetes / Docker Compose healthchecks."""
    start_time = getattr(request.app.state, "start_time", time.time())
    uptime = time.time() - start_time
    
    lgb_model = getattr(request.app.state, "lgb_model", None)
    feature_service = getattr(request.app.state, "feature_service", None)
    
    model_status = "LOADED" if lgb_model is not None else "UNINITIALIZED"
    fs_status = "CONNECTED" if (feature_service and getattr(feature_service, "redis_online", False)) else "LOCAL_FALLBACK"
    
    return HealthResponse(
        status="HEALTHY" if model_status == "LOADED" else "DEGRADED",
        model_version="1.0.0 (LightGBM Optuna-Tuned)",
        feature_store_status=fs_status,
        uptime_seconds=round(uptime, 2)
    )
