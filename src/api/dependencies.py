from typing import NamedTuple, Any
from fastapi import Request, HTTPException, status
import lightgbm as lgb

from src.models.explainability import FraudExplainer
from src.models.cost_router import DynamicCostRouter
from src.api.feature_service import FeatureService

class ScoringEngineContainer(NamedTuple):
    """Immutable dependency container holding pre-warmed ML singletons."""
    feature_service: FeatureService
    lgb_model: lgb.Booster
    explainer: FraudExplainer
    cost_router: DynamicCostRouter

def get_scoring_engine(request: Request) -> ScoringEngineContainer:
    """
    FastAPI Dependency Provider that supplies the pre-warmed ML engine container.
    Guarantees thread-safe access and raises HTTP 503 if any engine is uninitialized.
    """
    feature_service = getattr(request.app.state, "feature_service", None)
    lgb_model = getattr(request.app.state, "lgb_model", None)
    explainer = getattr(request.app.state, "explainer", None)
    cost_router = getattr(request.app.state, "cost_router", None)
    
    if None in (feature_service, lgb_model, explainer, cost_router):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Machine learning engines are not fully initialized."
        )
        
    return ScoringEngineContainer(
        feature_service=feature_service,
        lgb_model=lgb_model,
        explainer=explainer,
        cost_router=cost_router
    )
