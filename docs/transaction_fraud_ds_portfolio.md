# Flagship Real-Time Transaction Fraud Engine: Deep Research, Architecture & Implementation Blueprint (July 2026)

> **Executive Summary**: An exhaustive, research-backed blueprint for building a **production-grade, real-time transaction fraud detection platform**. This project is specifically designed to position an entry-level or junior Data Science candidate in the top 1% of applicants by solving the exact architectural, metric, and latency challenges faced by fraud engineering teams at companies like Stripe, Adyen, Block (Square), PayPal, Riskified, and Sift.

---

## 1. Comprehensive Dataset Research & Comparison Matrix

Selecting the right dataset is critical. Most candidate projects fail because they use anonymized PCA datasets where entity keys (`user_id`, `card_id`, `ip_address`) are missing, rendering real-time velocity feature engineering impossible.

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         DATASET EVALUATION FOR FRAUD DS                     │
 ├───────────────────┬───────────────────┬───────────────────┬─────────────────┤
 │ DATASET           │ TYPE & SIZE       │ FEATURE STRUCTURE │ VELOCITY FIT    │
 ├───────────────────┼───────────────────┼───────────────────┼─────────────────┤
 │ 1. Sparkov        │ Simulated E-comm  │ Raw Entity Keys & │ 🟢 PERFECT       │
 │    Data Generator │ ~1.8M tx (2 yrs)  │ Geo Coordinates   │   (Primary)     │
 ├───────────────────┼───────────────────┼───────────────────┼─────────────────┤
 │ 2. IEEE-CIS Fraud │ Real E-commerce   │ 393 Features +    │ 🟢 EXCELLENT    │
 │    Detection      │ ~590k tx (Kaggle) │ Device/ID Tables  │   (Secondary)   │
 ├───────────────────┼───────────────────┼───────────────────┼─────────────────┤
 │ 3. PaySim Mobile  │ Synthetic Money   │ Account-to-Account│ 🟡 GOOD         │
 │    Money          │ ~6.3M tx          │ Balance Flow      │   (Transfer)    │
 ├───────────────────┼───────────────────┼───────────────────┼─────────────────┤
 │ 4. ULB Credit     │ European Cards    │ 28 Anonymized PCA │ 🔴 POOR         │
 │    Card Fraud     │ ~284k tx          │ (No Entity IDs)   │   (Avoid)       │
 └───────────────────┴───────────────────┴───────────────────┴─────────────────┘
```

### Deep Dive Comparison: Why Choose Sparkov / IEEE-CIS?

| Dataset | Pros | Cons | Verdict for Project 1 |
| :--- | :--- | :--- | :--- |
| **Sparkov Credit Card Generator** | Contains raw `cc_num`, `merchant`, `category`, `amt`, `lat`, `long`, `unix_time`, `zip`, `city`. Simulates realistic card-testing bursts and geo-velocity (speed between transactions). | Synthetic (generated via Markov chains). | **BEST CHOICE for Feature Store & Velocity Engine**. Allows building 5m/1h/24h Redis counters and spatial distance metrics. |
| **IEEE-CIS Fraud Detection** | Real-world Vesta Corp transaction data. Rich identity tables, device info, email domain proxies, and real fraud patterns. | Highly complex; many anonymized V-features (`V1`-`V339`) requiring extensive EDA. | **GREAT ALTERNATIVE / SECONDARY BENCHMARK**. Excellent for practicing high-dimensional tabular ML. |
| **PaySim (Mobile Money)** | Great for account balance transfers and peer-to-peer (P2P) fraud (e.g. Venmo / Zelle / M-Pesa). | Lacks e-commerce attributes like IP address, device fingerprint, or merchant categories. | Good for P2P transfer projects, but less representative of card-not-present (CNP) e-commerce fraud. |
| **ULB Credit Card Dataset** | Very clean; widely used in tutorials; benchmark for imbalance algorithms. | **Features are PCA transformed (`V1`-`V28`)**. Timestamp is just seconds from 1st transaction; NO user IDs or card IDs. | **AVOID FOR FEATURE STORE PROJECTS**. Impossible to create velocity features (e.g. "tx count per card in 1 hour"). |

> **Recommendation**: Primary dataset = **IEEE-CIS Fraud Detection** (as per user selection). It provides highly realistic e-commerce fraud patterns and rich identity features.

---

## 2. Expanded Tech Stack & Architecture Integration

We expand the baseline stack (**Feast + Redis + LightGBM + FastAPI + SHAP**) with industry-standard MLOps, streaming, and monitoring technologies:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         EXPANDED PRODUCTION TECH STACK                      │
 ├───────────────────┬─────────────────────────────────────────────────────────┤
 │ COMPONENT         │ TECHNOLOGIES & PURPOSE                                  │
 ├───────────────────┼─────────────────────────────────────────────────────────┤
 │ Real-Time Ingest  │ Apache Kafka (Streaming events)                         │
 │ Feature Store     │ Feast (Feature Layer) + Redis (Online Key-Value <5ms)   │
 │ Offline Analytics │ DuckDB + Polars (Zero-leakage point-in-time SQL joins)  │
 │ Model Engine      │ LightGBM / XGBoost + Optuna (Hyperparameter Tuning)    │
 │ MLOps & Tracking  │ MLflow (Experiment tracking, model registry, metrics)   │
 │ Serving Endpoint  │ FastAPI + Uvicorn + Pydantic (Containerized REST API)   │
 │ Explainability    │ SHAP TreeExplainer (Real-time top-3 reason code generator)│
 │ Drift Monitoring  │ Evidently AI (Data & prediction drift on analyst feedback)│
 │ Load Stress Test  │ Locust / K6 (SLA latency stress testing up to 1,000 rps)│
 │ Orchestration     │ Docker Compose + Github Actions (CI/CD pipeline)        │
 └───────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 3. Competitive Analysis: Existing Projects vs. Our Project Novelty

### What 95% of Public Fraud Detection Repositories Do
Most GitHub repositories suffer from major limitations that hiring managers easily spot:
1. **Jupyter Notebook-Only**: Trained a Logistic Regression or XGBoost model on the ULB dataset in a single `.ipynb` notebook.
2. **Naive 0.5 Threshold**: Evaluated model accuracy using default 0.5 classification threshold.
3. **ROC-AUC Focus**: Reported high ROC-AUC (0.99) without measuring Precision-Recall curves or False Positive Rates.
4. **No Feature Store / Streaming**: Ignored real-time latency, sliding windows, and point-in-time correctness.
5. **Black Box Scoring**: Returned a raw probability score without explaining *why* a transaction was flagged.

### The 4 Key Novelties Introduced in Our Project

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         OUR 4 KEY PROJECT NOVELTIES                         │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ NOVELTY 1: DUAL-TIER FEATURE STORE (Redis Online + DuckDB Offline)          │
 │ • Zero-leakage temporal point-in-time joins for training                    │
 │ • Sub-5ms Redis key-value retrieval for online velocity (5m, 1h, 24h)       │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ NOVELTY 2: DYNAMIC TRANSACTION-VALUE AWARE COST ROUTER                      │
 │ • Adapts thresholding based on transaction dollar value ($10 vs $5,000)     │
 │ • Minimizes Total Cost = FN Loss + FP Customer Friction Loss                │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ NOVELTY 3: REAL-TIME SHAP REASON CODES + ANALYST FEEDBACK LOOP              │
 │ • Generates top-3 human-readable attribution codes per transaction           │
 │ • Endpoint for 30-day delayed chargeback labels triggering Evidently AI drift│
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ NOVELTY 4: EMPIRICAL SLA LOAD BENCHMARK (Locust / K6)                       │
 │ • Automated load testing suite proving sub-25ms p95 latency at 1,000 req/sec│
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Comprehensive Phase-by-Phase Implementation Plan

```mermaid
flowchart TD
    p1["Phase 1: Ingestion<br>Dataset Download & DuckDB Ingest"] --> p2["Phase 2: Feature Store<br>Point-in-time Joins & Feast Redis"]
    p2 --> p3["Phase 3: Model Engine<br>LightGBM Tuning & MLflow Registry"]
    p3 --> p4["Phase 4: Dynamic Router<br>Cost Matrix Threshold Optimization"]
    p4 --> p5["Phase 5: FastAPI Microservice<br>FastAPI + Redis + SHAP Reason Codes"]
    p5 --> p6["Phase 6: Drift & Feedback<br>Analyst Endpoint & Evidently AI"]
    p6 --> p7["Phase 7: SLA Stress Test<br>Locust Load Test (<25ms p95 SLA)"]
    p7 --> p8["Phase 8: Portfolio Release<br>Docker Compose & Documentation"]
```

---

## 5. Production Code Scaffolding & Architecture Blueprints

### 1. Offline Temporal Point-in-Time Join Engine (`src/features/point_in_time.py`)
```python
import duckdb

def build_point_in_time_velocity_features(db_path="data/transactions.duckdb"):
    """
    Computes zero-leakage sliding window velocity features using DuckDB.
    Guarantees feature calculation uses ONLY records strictly prior to current transaction timestamp.
    """
    con = duckdb.connect(db_path)
    
    query = """
    CREATE OR REPLACE TABLE train_velocity_features AS
    SELECT 
        t.trans_num,
        t.cc_num,
        t.trans_date_trans_time AS event_timestamp,
        t.amt,
        t.category,
        t.is_fraud,
        -- 5-Minute Velocity Count per Card
        COUNT(*) OVER (
            PARTITION BY t.cc_num 
            ORDER BY t.trans_date_trans_time 
            RANGE BETWEEN INTERVAL 5 MINUTE PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_5m,
        -- 1-Hour Velocity Count per Card
        COUNT(*) OVER (
            PARTITION BY t.cc_num 
            ORDER BY t.trans_date_trans_time 
            RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS tx_count_1h,
        -- 24-Hour Sum Amount per Card
        COALESCE(SUM(t.amt) OVER (
            PARTITION BY t.cc_num 
            ORDER BY t.trans_date_trans_time 
            RANGE BETWEEN INTERVAL 24 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ), 0.0) AS amt_sum_24h,
        -- Distinct Merchants in Last 1 Hour
        COUNT(DISTINCT t.merchant) OVER (
            PARTITION BY t.cc_num 
            ORDER BY t.trans_date_trans_time 
            RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND INTERVAL 1 SECOND PRECEDING
        ) AS distinct_merchants_1h
    FROM raw_transactions t
    ORDER BY t.trans_date_trans_time ASC;
    """
    con.execute(query)
    print("Point-in-time velocity feature table successfully generated with ZERO leakage.")
    con.close()

if __name__ == "__main__":
    build_point_in_time_velocity_features()
```

---

### 2. Dynamic Transaction-Value Aware Cost Matrix Router (`src/models/cost_router.py`)
```python
import numpy as np

class DynamicCostRouter:
    """
    Dynamically adjusts risk decision thresholds based on transaction dollar value.
    Higher transaction amounts have stricter thresholds due to severe Chargeback FN cost.
    """
    def __init__(self, base_cb_fee=25.0, friction_rate=0.02):
        self.base_cb_fee = base_cb_fee
        self.friction_rate = friction_rate

    def calculate_action(self, fraud_probability: float, amount: float) -> str:
        # Calculate expected loss of False Negative (FN) vs False Positive (FP)
        fn_cost = amount + self.base_cb_fee  # Stolen amount + bank chargeback fine
        fp_cost = (amount * self.friction_rate) + 5.0  # Missed interchange + customer annoyance LTV hit
        
        # Calculate optimal dynamic thresholds
        step_up_threshold = max(0.05, min(0.30, fp_cost / (fn_cost + fp_cost)))
        decline_threshold = max(0.50, min(0.85, (2.0 * fp_cost) / (fn_cost + fp_cost)))
        
        if fraud_probability < step_up_threshold:
            return "AUTO_APPROVE"
        elif fraud_probability < decline_threshold:
            return "STEP_UP_3DS"
        else:
            return "DECLINE"
```

---

### 3. FastAPI Microservice with Real-Time SHAP & Analyst Feedback (`src/api/main.py`)
```python
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import lightgbm as lgb
import shap
import redis
import numpy as np
import time
import json

app = FastAPI(title="Production Real-Time Fraud Engine & Analyst Platform")

# Load model, explainer, and Redis connection
model = lgb.Booster(model_file="models/fraud_lgb_model.txt")
explainer = shap.TreeExplainer(model)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class TransactionEvent(BaseModel):
    transaction_id: str
    card_number: str
    amount: float
    merchant: str
    category: str

class AnalystFeedback(BaseModel):
    transaction_id: str
    actual_label: int  # 1 = Confirmed Fraud (Chargeback), 0 = Legitimate
    analyst_notes: str

@app.post("/v1/score")
def score_transaction(event: TransactionEvent):
    start_time = time.perf_counter()
    
    # 1. Fetch Online Velocity Features from Redis (<3ms)
    user_key = f"card:{event.card_number}:velocity"
    features = r.hgetall(user_key)
    
    tx_count_5m = int(features.get('tx_count_5m', 0))
    tx_count_1h = int(features.get('tx_count_1h', 0))
    amt_sum_24h = float(features.get('amt_sum_24h', 0.0))
    
    # 2. Vectorize for Model Inference (<5ms)
    feature_vector = np.array([[event.amount, tx_count_5m, tx_count_1h, amt_sum_24h]])
    feature_names = ['amount', 'tx_count_5m', 'tx_count_1h', 'amt_sum_24h']
    
    fraud_prob = float(model.predict(feature_vector)[0])
    
    # 3. Dynamic Value Router Decision (<1ms)
    fn_cost = event.amount + 25.0
    fp_cost = (event.amount * 0.02) + 5.0
    step_up_threshold = max(0.05, min(0.30, fp_cost / (fn_cost + fp_cost)))
    decline_threshold = max(0.50, min(0.85, (2.0 * fp_cost) / (fn_cost + fp_cost)))
    
    if fraud_prob < step_up_threshold:
        action = "APPROVE"
    elif fraud_prob < decline_threshold:
        action = "STEP_UP_3DS"
    else:
        action = "DECLINE"
        
    # 4. Generate SHAP Reason Codes (<8ms)
    shap_vals = explainer.shap_values(feature_vector)[0]
    top_indices = np.argsort(-np.abs(shap_vals))[:3]
    reason_codes = [
        {"feature": feature_names[i], "impact_score": round(float(shap_vals[i]), 4)}
        for i in top_indices
    ]
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    return {
        "transaction_id": event.transaction_id,
        "fraud_probability": round(fraud_prob, 4),
        "action": action,
        "reason_codes": reason_codes,
        "latency_ms": round(latency_ms, 2)
    }

@app.post("/v1/analyst/feedback")
def submit_analyst_feedback(feedback: AnalystFeedback, background_tasks: BackgroundTasks):
    """
    Accepts delayed 30-90 day chargeback labels from fraud analysts.
    Logs feedback to Redis stream for Evidently AI drift analysis.
    """
    r.xadd("stream:analyst_feedback", {
        "transaction_id": feedback.transaction_id,
        "actual_label": str(feedback.actual_label),
        "timestamp": str(time.time())
    })
    return {"status": "SUCCESS", "message": "Analyst feedback recorded for drift monitoring."}
```

---

### 4. Locust SLA Latency Load Test Script (`tests/locustfile.py`)
```python
from locust import HttpUser, task, between
import random
import uuid

class FraudEngineLoadTest(HttpUser):
    wait_time = between(0.001, 0.005)  # Simulate high-frequency transactions

    @task
    def score_transaction(self):
        payload = {
            "transaction_id": str(uuid.uuid4()),
            "card_number": f"4000123456{random.randint(1000, 9999)}",
            "amount": round(random.uniform(5.0, 1500.0), 2),
            "merchant": "merchant_amazon_prime",
            "category": "online_retail"
        }
        self.client.post("/v1/score", json=payload)
```

---

## 6. How This Project Beats 99% of Candidates in Interviews

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         INTERVIEW TALKING POINTS & POSITIONING              │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ 1. "I didn't just train a model in a notebook—I built a production-grade    │
 │    streaming feature store using Feast and Redis achieving sub-25ms SLA."   │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ 2. "I engineered zero-leakage point-in-time sliding window features in       │
 │    DuckDB across 5m, 1h, and 24h temporal horizons."                        │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ 3. "Instead of a static 0.5 threshold, I created a Dynamic Cost Matrix      │
 │    Router that scales cutoff thresholds based on transaction dollar amounts."│
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ 4. "Every prediction outputs top-3 SHAP reason codes for fraud analyst       │
 │    workflows, and accepts delayed chargeback labels for drift monitoring."  │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Frontend & User Interface Architecture (The Fraud Operations Platform)

In real-world fraud engineering (Stripe Radar, Adyen Risk Management, Sift Console, Riskified Merchant Center), the frontend is **not just a simple chart**—it is a **dual-purpose web application**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         FRONTEND UI ARCHITECTURE                            │
 ├──────────────────────────────────────┬──────────────────────────────────────┤
 │ APP A: FRAUD ANALYST WORKBENCH       │ APP B: CHECKOUT & 3DS CHALLENGE PORTAL│
 │ (Internal Admin Dashboard)           │ (Customer-Facing Simulation)         │
 ├──────────────────────────────────────┼──────────────────────────────────────┤
 │ 1. Live Streaming Transaction Feed   │ 1. E-Commerce Payment Form            │
 │ 2. Transaction Inspector & SHAP Chart│ 2. Dynamic Step-Up Modal (3DS / OTP) │
 │ 3. Chargeback Labeling & Feedback    │ 3. Instant Decision Result (Approved/│
 │ 4. Evidently AI Drift & Metric Monitor│    Blocked / Verified)               │
 └──────────────────────────────────────┴──────────────────────────────────────┘
```

### 1. App A: Fraud Analyst Workbench (React / Streamlit / TailwindCSS)
- **Live Transaction Ticker**: Real-time table streaming inbound payment events over WebSockets/SSE. Displays transaction ID, amount, card mask, risk probability score (0-100), decision pill (`APPROVE` green, `STEP_UP_3DS` amber, `DECLINE` red), and latency (<25ms).
- **Transaction Inspector Drawer**: Clicking any transaction opens a detailed panel:
  - **SHAP Reason Code Waterfall Chart**: Visualizes the top 3 features driving the risk score (e.g. `tx_count_5m = 7 (+0.38 risk)`, `amt_to_30d_avg = 14.2x (+0.29 risk)`).
  - **Velocity Profile Grid**: Displays 5m, 1h, 24h counters and IP/device association map.
  - **Analyst Decision Panel**: Buttons for fraud analysts to record confirmed chargebacks (`Mark Fraud`) or whitelist false positives (`Mark Legitimate`), sending feedback to `/v1/analyst/feedback`.
- **System Metrics & Drift Dashboard**: Tracks real-time PR-AUC, financial dollar savings, and Evidently AI feature drift warnings.

### 2. App B: Customer-Facing Checkout Simulation Portal
- **Interactive Checkout Interface**: Lets the user or hiring manager test a transaction by adjusting amount, card number, and velocity.
- **Dynamic 3D-Secure (3DS) Trigger**: If the transaction triggers a medium risk score ($0.15 \le P(\text{fraud}) < 0.70$), the UI launches an interactive SMS / OTP Step-Up Authentication modal to demonstrate friction-aware fraud handling.

---

## 8. Execution Checklist for Launching via Teamwork

- [x] Research & Dataset comparison completed (Sparkov vs IEEE-CIS vs PaySim vs ULB).
- [x] Tech stack expanded with Kafka/Redpanda, DuckDB, Feast, Redis, LightGBM, MLflow, FastAPI, SHAP, Evidently AI, Locust, React/Streamlit UI.
- [x] 4 Key Novelties established to stand out against traditional candidate portfolios.
- [x] `prompt_draft.md` artifact updated and ready for launch.

> **To launch the autonomous multi-agent execution team**, reply with **"Launch teamwork"** or **"Go"**.
