# Career Resume Prompt Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the complete technical, quantitative, and architectural facts of the Real-Time Transaction Fraud Engine into the master resume prompt document (`gemini-code-1788283802388.md`) adhering strictly to the zero-deletion constraint, 2026 ATS optimization standards, and project memory logging rules.

**Architecture:** Append the Real-Time Transaction Fraud Engine with 13 pre-de-fluffed, unbolded-verb, ATS-optimized bullets categorized into Tracks A, B, and C under `## VERIFIED PROJECT FACTS`. Update `## TECHNICAL SKILLS MASTER LIST` and `## MANDATORY GRAMMATICAL & SYNTAX AUDIT` with verified tools, compound modifiers, and framework symbols. Validate integrity using a Python diff check to guarantee zero deletions from the original document.

**Tech Stack:** Markdown, Python (for verification scripts), Git.

---

### File Map
- **Modify:** `C:\Users\Aarya\Gemini_cli_testing\Career\gemini-code-1788283802388.md` (Add project facts, skills, and grammar rules)
- **Modify:** `C:\Users\Aarya\Gemini_cli_testing\Transaction-Fraud\decision.md` (Record architecture decision)
- **Modify:** `C:\Users\Aarya\Gemini_cli_testing\Transaction-Fraud\memory.md` (Append progress log)
- **Test:** `scratch/verify_resume_prompt_integration.py` (Verify zero deletions and format compliance)

---

### Task 1: Update Target Resume Prompt Document

**Files:**
- Modify: `C:\Users\Aarya\Gemini_cli_testing\Career\gemini-code-1788283802388.md`

- [ ] **Step 1: Backup original file for zero-deletion verification**
Make a copy of `gemini-code-1788283802388.md` to `scratch/gemini-code-original-backup.md`.

- [ ] **Step 2: Append project facts under `## VERIFIED PROJECT FACTS`**
Add the project header, GitHub repository link, and the 13 categorized bullets under Tracks A, B, and C:

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

- [ ] **Step 3: Update `## TECHNICAL SKILLS MASTER LIST`**
Add:
- `LightGBM`, `TreeSHAP`, `Optuna`, `Feast (Feature Store)` to `**Machine Learning & AI:**`
- `DuckDB` to `**Languages & Databases:**`
- `Evidently AI`, `Locust` to `**Data Visualization & Libraries:**`
- `FastAPI`, `Uvicorn`, `Docker Compose`, `Apache Kafka`, `Redpanda`, `Nginx`, `Pytest` to `**Cloud & Infrastructure:**`

- [ ] **Step 4: Update `## MANDATORY GRAMMATICAL & SYNTAX AUDIT`**
Add new compound modifiers (`dual-tier feature store`, `point-in-time temporal joins`, `sub-25ms latency SLA`, `value-adaptive decision router`, `tri-state payment routing`, `multi-objective hyperparameter tuning`, `three-way decision boundary`, `adverse-action reason codes`, `120-day statement arbitration cycle`, `sliding-window velocity engine`).
Add new framework symbols (`LightGBM`, `DuckDB`, `Feast`, `FastAPI`, `Uvicorn`, `Locust`, `Evidently AI`, `Apache Kafka`, `Redpanda`, `TreeSHAP`, `Optuna`).

---

### Task 2: Automated Verification of Document Integrity & ATS Rules

**Files:**
- Test script: `scratch/verify_resume_prompt_integration.py`

- [ ] **Step 1: Write the automated verification script**
Create `scratch/verify_resume_prompt_integration.py` that verifies:
1. Every line from `gemini-code-original-backup.md` exists in the modified file (zero lines removed).
2. Exactly 13 new bullets exist under the project.
3. No opening verb is bolded.
4. No `<` or `>` symbols appear in the bullets.
5. All newly added skills are present in the Technical Skills list.

- [ ] **Step 2: Run verification script and ensure PASS**
Run: `python scratch/verify_resume_prompt_integration.py`
Expected: `ALL CHECKS PASSED: Zero deletions, 13 verified bullets, 100% ATS compliant.`

---

### Task 3: Decision & Memory Logging

**Files:**
- Modify: `decision.md`
- Modify: `memory.md`

- [ ] **Step 1: Document in `decision.md`**
Record the career resume prompt integration decision, including the ATS research rationale, zero-deletion policy, and role-categorized bullet pool.

- [ ] **Step 2: Append steps to `memory.md`**
Log the exact additions and verification steps made.

- [ ] **Step 3: Git status check & pre-commit explanation**
Provide the user with a detailed summary of changes and explain before any git operations.
