import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import lightgbm as lgb

from src.models.explainability import FraudExplainer
from src.models.cost_router import DynamicCostRouter
from src.api.feature_service import FeatureService
from src.api.routes import scoring, feedback, health, stream

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for zero-overhead startup and shutdown.
    Pre-warms the LightGBM model, SHAP TreeExplainer, Dynamic Cost Router, and Feature Store connections.
    """
    print("[FastAPI Lifespan] Initializing Production Fraud Decisioning Engine...")
    app.state.start_time = time.time()
    
    # 1. Pre-warm SHAP TreeExplainer & Shared LightGBM Booster
    model_path = os.environ.get("MODEL_PATH", "models/fraud_lgb_model.txt")
    if not os.path.exists(model_path):
        # Fallback to parent path if running from subfolder
        model_path = os.path.join("..", model_path)
        
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}! Train model first via train_lgb.py.")

    app.state.explainer = FraudExplainer(model_path=model_path)
    app.state.lgb_model = app.state.explainer.model
    feature_names = app.state.lgb_model.feature_name()
    print(f"[FastAPI Lifespan] Loaded LightGBM booster with {len(feature_names)} features.")
        
    # 2. Initialize Feature Hydration Service
    app.state.feature_service = FeatureService(
        feature_store_repo="feature_repo",
        feature_names=feature_names
    )
    print("[FastAPI Lifespan] FeatureService initialized.")
    
    # 4. Initialize Dynamic Cost Router
    app.state.cost_router = DynamicCostRouter()
    print("[FastAPI Lifespan] DynamicCostRouter initialized.")
    
    print("[FastAPI Lifespan] Real-Time Fraud Microservice ready to receive traffic.")
    yield
    
    # Teardown logic
    print("[FastAPI Lifespan] Shutting down Fraud Microservice...")
    app.state.lgb_model = None
    app.state.explainer = None
    app.state.feature_service = None
    app.state.cost_router = None

# Initialize FastAPI application
app = FastAPI(
    title="Real-Time Transaction Fraud Detection Engine",
    version="1.0.0",
    description="Production-grade real-time fraud scoring microservice featuring dual-tier feature hydration, sub-5ms LightGBM inference, SHAP localized reason codes, and dynamic Bayesian cost router.",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing (CORS) Middleware
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Execution Timing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
    return response

# Register API Routers
app.include_router(health.router)
app.include_router(scoring.router)
app.include_router(feedback.router)
app.include_router(stream.router)

# Standalone Static Frontend Serving (for all-in-one containers such as Hugging Face Spaces)
from pathlib import Path
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_static_dir = Path(__file__).resolve().parent.parent.parent / "static"
if not _static_dir.exists():
    _frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if _frontend_dist.exists():
        _static_dir = _frontend_dist

if _static_dir.exists() and (_static_dir / "index.html").exists():
    _assets_dir = _static_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="spa_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Never intercept API, docs, or health endpoints
        if (
            full_path.startswith("v1")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path == "openapi.json"
            or full_path == "health"
        ):
            raise HTTPException(status_code=404, detail="API route not found")

        target_file = _static_dir / full_path
        if full_path and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(_static_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)
