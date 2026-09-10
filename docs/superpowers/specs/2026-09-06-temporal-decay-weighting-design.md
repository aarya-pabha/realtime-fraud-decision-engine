# Technical Specification: Temporal Decay Sample Weighting for PR-AUC Optimization

- **Author:** Antigravity Agent & User Pair
- **Date:** 2026-09-06
- **Status:** Approved for Implementation
- **Target Branch:** `feature/model-optimization-cost-sensitive`
- **Scope:** LightGBM Model Engine & Training Pipeline

---

## 1. Executive Summary & Problem Statement

### 1.1 Context
In the Real-Time Transaction Fraud Detection Engine, the LightGBM booster achieves strong discrimination on the Month 5 validation set:
- **Validation (Month 5, Days 121–150):** ROC-AUC = `0.9178`, PR-AUC = `0.5506`
- **Holdout Test (Month 6, Days 151–183):** ROC-AUC = `0.9003`, PR-AUC = `0.5063`

The `0.5506 -> 0.5063` drop in PR-AUC is driven by **temporal concept drift**: fraud patterns, device signatures, and card-testing techniques evolve across the 6-month IEEE-CIS window. Currently, training on Days 1–120 (~410,601 transactions) applies **uniform weighting**, forcing tree split algorithms to expend capacity on 4-month-old stale fraud patterns that no longer resemble Month 6 attacks.

### 1.2 Objective
Implement **Exponential Temporal Decay Weighting** with **Dual-Class Invariant Normalization** on the training set to prioritize recent fraud dynamics, improving out-of-time Month 6 PR-AUC without distorting probability calibration, increasing realized financial loss, or compromising the sub-25ms p95 latency SLA.

---

## 2. Mathematical Formulation

### 2.1 Exponential Temporal Decay
For training sample $i \in \{1, \dots, N_{\text{train}}\}$ with timestamp $t_i = \text{TransactionDT}_i$ and training horizon upper bound $t_{\max} = 120 \times 86,400$ seconds:

$$\Delta t_i = \frac{t_{\max} - t_i}{86,400} \quad (\text{transaction age in days}, \ 0 \le \Delta t_i \le 120)$$

With half-life $T_{1/2} = 60.0\text{ days}$:

$$\tilde{w}_i = 2^{-\frac{\Delta t_i}{60.0}} = \exp\left(-\frac{\ln(2)}{60.0} \cdot \Delta t_i\right)$$

- Day 120 (most recent): $\Delta t_i = 0 \implies \tilde{w}_i = 1.00$
- Day 60 (training midpoint): $\Delta t_i = 60 \implies \tilde{w}_i = 0.50$
- Day 1 (oldest transaction): $\Delta t_i = 119 \implies \tilde{w}_i \approx 0.25$

### 2.2 Dual-Class Invariant Normalization
To prevent perturbing the effective positive-to-negative class prior (which would distort output probabilities and break the Level 3+4 Dynamic Cost Router), fraud ($y_i = 1$) and legitimate ($y_i = 0$) weights are normalized separately:

$$w_i = \begin{cases} 
\tilde{w}_i \cdot \frac{N_{\text{fraud}}}{\sum_{j: y_j=1} \tilde{w}_j} & \text{if } y_i = 1 \\[10pt]
\tilde{w}_i \cdot \frac{N_{\text{legit}}}{\sum_{j: y_j=0} \tilde{w}_j} & \text{if } y_i = 0 
\end{cases}$$

**Mathematical Invariant:**
$$\frac{\sum_{i: y_i=1} w_i}{\sum_{j: y_j=0} w_j} = \frac{N_{\text{fraud}}}{N_{\text{legit}}} \equiv \text{Original Class Balance}$$

This guarantees:
1. `scale_pos_weight: 6.77` operates on the exact original effective class imbalance.
2. Uncalibrated margin outputs remain centered, preventing systematic probability inflation or deflation.
3. Decision boundaries in `DynamicCostRouter` remain mathematically aligned.

---

## 3. Architecture & Implementation Design

### 3.1 Component Architecture
1. **Weight Computation Function (`src/models/temporal_weighting.py`):**
   A pure, vectorized NumPy function computing $w_i$:
   ```python
   def compute_temporal_decay_weights(
       y: np.ndarray,
       timestamps: np.ndarray,
       half_life_days: float = 60.0,
       t_max: float = 120.0 * 86400.0
   ) -> np.ndarray:
       delta_days = np.maximum(0.0, (t_max - timestamps) / 86400.0)
       raw_weights = np.power(2.0, -delta_days / half_life_days)
       
       # Dual-class invariant normalization
       weights = np.empty_like(raw_weights)
       fraud_mask = (y == 1)
       legit_mask = (y == 0)
       
       weights[fraud_mask] = raw_weights[fraud_mask] * (np.sum(fraud_mask) / np.sum(raw_weights[fraud_mask]))
       weights[legit_mask] = raw_weights[legit_mask] * (np.sum(legit_mask) / np.sum(raw_weights[legit_mask]))
       return weights
   ```
2. **Exploration & Benchmarking (`src/models/explorations/tune_temporal_decay_lgb.py`):**
   - Trains LightGBM with sample weights on `dtrain = lgb.Dataset(X_train, label=y_train, weight=weights)`.
   - Validates on Month 5 and tests on Month 6 with unweighted evaluation.
   - Evaluates with `DynamicCostRouter.batch_route_and_evaluate()`.
3. **Production Model Training (`src/models/train_lgb.py`):**
   - Incorporates temporal decay weights upon passing all verification guardrails.
   - Logs metrics, weights distribution, and model artifacts to local SQLite MLflow (`sqlite:///mlruns.db`).

---

## 4. Verification Guardrails ("Do No Harm")

The new model must strictly satisfy all 6 operational guardrails:

| Guardrail Metric | Baseline Value | Required Threshold | Rationale |
| :--- | :---: | :---: | :--- |
| **1. Test PR-AUC** | `0.5063` | **$> 0.5063$** | Must demonstrate positive rank-order gain on holdout |
| **2. Test ROC-AUC** | `0.9003` | **$\ge 0.9000$** | Global discrimination must not degrade |
| **3. Brier Calibration Score** | `0.0310` | **$\le 0.0310$** | Probability calibration must not be damaged |
| **4. Realized Financial Loss** | **$95,688.32** | **$\le \$95,688.32$** | Must not increase business financial losses |
| **5. Chargeback Ratio** | `0.40%` | **$\le 0.45\%$** | Strict regulatory safety (Visa <1.5%, Mastercard <1.0%) |
| **6. Microservice p95 Latency** | `19.3ms` | **$< 25.0\text{ms}$** | Preserves C++ TreeSHAP structure and sub-25ms SLA |

---

## 5. Decision & Rollback Protocol
- If all 6 guardrails pass: Update `models/fraud_lgb_model.txt`, re-run full test suite (`pytest`), log to MLflow, and update `decision.md`.
- If any guardrail fails: Retain the existing champion production model and document the rejection rationale in `decision.md`.
