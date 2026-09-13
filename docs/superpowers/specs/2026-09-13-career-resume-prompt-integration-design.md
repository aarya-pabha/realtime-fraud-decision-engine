# Technical Design Specification: Career Resume Prompt Integration (Real-Time Transaction Fraud Engine)

**Date:** 2026-09-13  
**Status:** Approved by User  
**Target Document:** `C:\Users\Aarya\Gemini_cli_testing\Career\gemini-code-1788283802388.md`  
**Repository:** `Transaction-Fraud` (`aarya-pabha/realtime-fraud-decision-engine`)

---

## 1. Overview & Objectives
The goal of this task is to integrate the complete technical, quantitative, and architectural facts of the **Real-Time Transaction Fraud Engine** into the user's master resume-building prompt document (`gemini-code-1788283802388.md`). 

This document serves as the foundational knowledge base that Claude uses to construct tailored, ATS-friendly, single-page resumes across various target roles.

### Non-Negotiable Constraints:
1. **Append/Add Only:** Never delete or alter any existing project facts, work experience, guidelines, or candidate data from the target document.
2. **Zero Fabrication:** Every metric, parameter, and architectural claim must match verified code and empirical benchmark evaluations from `decision.md`, `memory.md`, and evaluation reports.
3. **ATS & Recruiter Optimization (2026 Standards):**
   - Natural language, complete sentences conforming to the Google XYZ format (*Accomplished X as measured by Y by doing Z*).
   - No code syntax fragments (`pred_contrib=True`), mathematical formulas (`w_i = 2^{-\Delta t_i / T_{1/2}}`), or obscure low-level C libraries (`libjemalloc2`, `FastHttpUser`).
   - No `<` or `>` symbols in compliance text to prevent XML tokenization bugs in older ATS parsers.
   - Explicit inclusion of high-frequency ATS skills taxonomy keywords (`Data Drift`, `Feature Store`, `Point-in-Time Joins`, `SLA Benchmarking`, `LightGBM`, `FastAPI`).
4. **Style & Voice Adherence:**
   - Opening action verbs are unbolded (matching existing project facts).
   - Strict verb diversity: 13 unique verbs drawn from the pre-approved pool (`Trained`, `Fine-tuned`, `Diagnosed`, `Evaluated`, `Engineered`, `Filtered`, `Resolved`, `Benchmarked`, `Integrated`, `Designed`, `Developed`, `Enforced`, `Implemented`).
   - Standard compound modifier hyphenation and framework casing.

---

## 2. Detailed Content Specifications for Target Document

### Component A: Addition to `## VERIFIED PROJECT FACTS — NEVER FABRICATE BEYOND THIS`

Insert after the existing projects:

```markdown
**Real-Time Transaction Fraud Engine** *(alt title: Production Real-Time Fraud Detection Platform; Dual-Tier Feature Store & Real-Time ML Decision Engine; High-Throughput Fraud Scoring & Dynamic Cost Router)* — DuckDB, Redis, Feast, Apache Kafka, Redpanda, LightGBM, Optuna, TreeSHAP, FastAPI, Pydantic V2, Uvicorn, Docker Compose, Nginx, Locust, Evidently AI, MLflow, Pytest
- GitHub: https://github.com/aarya-pabha/realtime-fraud-decision-engine

Track A — Machine Learning Engineering & Applied Modeling:
- Trained a production LightGBM classifier across 590,000+ IEEE-CIS transactions using a strict 3-way temporal split, preventing lookahead leakage while achieving a 0.9003 Test ROC-AUC and 0.5063 Test PR-AUC.
- Fine-tuned gradient boosted tree hyperparameters via 45 multi-objective Optuna trials with Knee-Point Euclidean selection, simultaneously maximizing validation PR-AUC (0.5506) and ROC-AUC (0.9178) while logging all artifacts to a local MLflow registry.
- Diagnosed the payment routing calibration trap, demonstrating that post-hoc isotonic probability calibration deflated risk scores and provoked a 3.5x fraud loss surge ($35,200 to $122,700) that breached Mastercard's 1.0% regulatory chargeback ceiling.
- Evaluated exponential temporal decay sample weighting with dual-class normalization across 410,000 training records, lifting validation PR-AUC to 0.5757 while cutting holdout false customer declines by 3.7%.

Track B — Real-Time Systems, Feature Store & Low-Latency MLOps:
- Engineered a dual-tier Feast feature store with a DuckDB offline sliding-window velocity engine and Redis online store, executing zero-leakage point-in-time joins across 72 domain features with sub-5ms online feature hydration.
- Filtered 339 collinear raw features down to 33 medoid representatives via correlation-based clustering, preserving over 99.6% of fraud class variance while slashing online Redis memory usage by 90.3%.
- Resolved scoring latency bottlenecks by integrating C++ TreeSHAP into an asynchronous FastAPI engine with conditional adverse-action routing, skipping attribution compute on clean approvals to slash median latency to 3.5ms and cut CPU utilization by 38.6%.
- Benchmarked microservice throughput under sustained 100-user concurrent load across 2,700+ requests with Locust, verifying zero request failures and a 19.0ms p95 latency against a strict 25.0ms contractual SLA.
- Integrated multi-container orchestration via Docker Compose, provisioning Redis 7, Redpanda Kafka broker, FastAPI with single-thread concurrency controls, and an Nginx reverse proxy with keepalive connection pooling on an isolated bridge network.

Track C — Financial Decision Intelligence, Dynamic Routing & Drift Operations:
- Designed a value-adaptive Bayesian dynamic cost router that maps transaction amounts to tri-state decisions (Approve, 3DS Challenge, Decline), using EMV 3D-Secure as a low-cost challenge buffer to trigger merchant liability shift on high-risk transactions.
- Developed a spend-tier routing policy evaluated on 92,400+ holdout transactions, slashing financial loss from $338,700 to $95,700 to deliver $243,000+ in net savings (71.8% loss reduction) and cut false customer declines by 63.3%.
- Enforced strict portfolio risk compliance, maintaining a 0.40% realized chargeback ratio to comfortably outperform Visa VAMP (under 1.50%) and Mastercard ECP (under 1.00%) excessive chargeback monitoring thresholds.
- Implemented an Evidently AI drift monitoring pipeline tracking feature-level data drift via Wasserstein distances and prediction score divergence, backed by an SQLite analyst dispute feedback loop modeled on a 120-day delayed feedback maturity lifecycle.
```

---

### Component B: Updates to `## TECHNICAL SKILLS MASTER LIST — only ever pull from this, never add beyond it`

Update the skill categories by adding only genuine, verified technologies used in this project:
- **Machine Learning & AI:** Add `LightGBM`, `TreeSHAP`, `Optuna`, `Feast (Feature Store)`
- **Languages & Databases:** Add `DuckDB`
- **Data Visualization & Libraries:** Add `Evidently AI`, `Locust`
- **Cloud & Infrastructure:** Add `FastAPI`, `Uvicorn`, `Docker Compose`, `Apache Kafka`, `Redpanda`, `Nginx`, `Pytest`

---

### Component C: Updates to `## MANDATORY GRAMMATICAL & SYNTAX AUDIT`

1. **Compound Modifier Hyphenation:**
   Add:
   - `dual-tier feature store`
   - `point-in-time temporal joins`
   - `sub-25ms latency SLA`
   - `value-adaptive decision router`
   - `tri-state payment routing`
   - `multi-objective hyperparameter tuning`
   - `three-way decision boundary`
   - `adverse-action reason codes`
   - `120-day statement arbitration cycle`
   - `sliding-window velocity engine`

2. **Standard Casing on Framework Symbols:**
   Add:
   - `LightGBM`, `DuckDB`, `Feast`, `FastAPI`, `Uvicorn`, `Locust`, `Evidently AI`, `Apache Kafka`, `Redpanda`, `TreeSHAP`, `Optuna`

---

## 3. Verification & Validation Plan
1. **Diff Integrity Verification:** Ensure `git diff` on `gemini-code-1788283802388.md` reveals 0 deletions and only additions.
2. **Grammar & Punctuation Audit:** Confirm every bullet point has a terminating period, serial comma, and no unbolded or duplicate opening action verbs.
3. **Audit Log Maintenance:** Record all updates in `decision.md` and append steps to `memory.md`.
