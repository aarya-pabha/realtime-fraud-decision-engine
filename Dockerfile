# ==============================================================================
# All-in-One Multi-Stage Production Dockerfile for Hugging Face Spaces
# Builds React SPA + Runs FastAPI Decisioning Engine, DuckDB & In-Memory Replay
# ==============================================================================

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime API & Decisioning Engine
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

WORKDIR /app

# Install OpenMP runtime and high-performance jemalloc allocator
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 libjemalloc2 && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user (Hugging Face Spaces default UID 1000)
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data && \
    chown -R user:user /app

# Copy application source code and pre-warmed artifacts
COPY --chown=user:user src/ /app/src/
COPY --chown=user:user feature_repo/ /app/feature_repo/
COPY --chown=user:user models/ /app/models/
COPY --chown=user:user data/ /app/data/
COPY --chown=user:user feature_store.duckdb /app/feature_store.duckdb

# Copy built frontend assets from Stage 1 into /app/static
COPY --from=frontend-builder --chown=user:user /frontend/dist /app/static

USER user

EXPOSE 7860

HEALTHCHECK --interval=15s --timeout=3s --retries=3 --start-period=15s \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:7860/v1/health').status == 200 else 1)"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--loop", "uvloop", "--http", "httptools"]
