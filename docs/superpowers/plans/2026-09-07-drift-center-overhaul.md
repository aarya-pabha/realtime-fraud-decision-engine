# Drift & Stability Center Comprehensive Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the Drift & Stability Center (`frontend/src/components/DriftView.tsx`) with an interactive feature-level Wasserstein drift bar chart (Recharts), live SQLite dispute feedback telemetry, a 30–120 day chargeback maturity lifecycle rail, on-demand retrospective drift analysis, and `/design-taste-frontend` typography polish.

**Architecture:** 
1. Backend: Harden `/v1/stream/drift` in `src/api/routes/stream.py` and `src/frontend/drift_service.py` to reliably return column-level Wasserstein distances and live `feedback_store.sqlite` dispute statistics.
2. Frontend: Update `types.ts` with drift interfaces. Build a dual-column layout in `DriftView.tsx` featuring (a) Top 3 Metric Cards with Title Case and math notation, (b) Recharts Feature Drift Bar Chart with `0.10` alert threshold reference line, (c) Live Dispute Feedback Buffer & Visa/Mastercard regulatory compliance telemetry, (d) 30–120 Day Maturity Lifecycle Rail, and (e) on-demand drift execution button with loading feedback.

**Tech Stack:** React 19, TypeScript, Recharts, Lucide Icons, Tailwind CSS v4, FastAPI, SQLite, DuckDB, Evidently AI, Docker Compose.

---

### Task 1: Backend Drift Endpoint & Service Hardening

**Files:**
- Modify: `src/frontend/drift_service.py`
- Modify: `src/api/routes/stream.py`
- Test: `tests/test_stream_api.py`

- [x] **Step 1: Update `src/frontend/drift_service.py`**
Ensure `DriftMonitoringService` includes `compute_drift_report` as an alias to `run_drift_analysis()`, includes comprehensive fallback column metrics for `TransactionAmt`, `tx_count_5m`, `amt_sum_24h`, `prediction`, and `card_tenancy_d1`, and accurately reads `data/feedback_store.sqlite`.

- [x] **Step 2: Update `src/api/routes/stream.py`**
Verify `GET /v1/stream/drift` executes `drift_service.run_drift_analysis()` and add `POST /v1/stream/drift/run` to trigger fresh on-demand evaluation.

- [x] **Step 3: Add test in `tests/test_stream_api.py`**
Add `test_stream_drift_endpoint(client)` asserting 200 OK, `drift_status`, `drift_by_columns`, and `feedback_summary`.

- [x] **Step 4: Run tests**
Run: `pytest tests/test_stream_api.py -v`
Expected: 4 passed.

---

### Task 2: Frontend Types & Drift Data Contract

**Files:**
- Modify: `frontend/src/types.ts`

- [x] **Step 1: Add Drift Interfaces**
Define:
- `ColumnDriftInfo` (`drift_detected: boolean`, `drift_score: number`, `stat_test: string`)
- `FeedbackSummary` (`total_disputes: number`, `confirmed_frauds: number`, `confirmed_legit: number`, `chargeback_rate_pct: number`)
- `DriftReportResponse` (`drift_status: string`, `dataset_drift: boolean`, `number_of_drifted_columns: number`, `drift_share: number`, `drift_by_columns: Record<string, ColumnDriftInfo>`, `feedback_summary: FeedbackSummary`)

---

### Task 3: Comprehensive `DriftView.tsx` Overhaul

**Files:**
- Modify: `frontend/src/components/DriftView.tsx`

- [x] **Step 1: Implement Live Data Polling & State**
Fetch `/v1/stream/drift` on mount and provide an interactive `handleRunAnalysis` handler with animated spinner and completion toast.

- [x] **Step 2: Build Top 3 Metric Cards**
- Replace screaming uppercase with Title Case (`Transaction Amount Drift`, `Velocity Burst (5m)`, `Model PR-AUC Stability`).
- Include mathematical notation ($W_1 = 0.038$, $D_{\text{JS}} = 0.021$, $\Delta \text{PR-AUC} = 0.506$).
- Include soft status pills (`Safe • Within Threshold`).

- [x] **Step 3: Build Recharts Feature Drift Bar Chart**
- Feature dimensions: `Transaction Amount`, `5m Card Velocity`, `24h Spend Sum`, `Prediction Score P(Fraud)`, `Account Age (D1 Delta)`.
- Dashed reference line at `0.10` alert threshold.
- Custom tooltip with formatted metrics and status tags.
- Responsive container with clean styling matching Tasko aesthetic.

- [x] **Step 4: Build Dispute Feedback Queue & Regulatory Telemetry**
- Live counter of disputes logged from SQLite.
- Confirmed fraud vs legitimate count bars.
- Visa VAMP (<1.50%) and Mastercard ECP (<1.00%) compliance status badges.

- [x] **Step 5: Build 30–120 Day Maturity Lifecycle Step Rail**
- 4-step horizontal rail:
  1. `Day 0: Real-Time Scoring` (LightGBM sub-25ms)
  2. `Day 1–30: Statement Review` (Cardholder billing cycle)
  3. `Day 30–90: Dispute Window` (Bank retrieval and chargebacks)
  4. `Day 120: Maturity Close` (Retrospective Evidently AI drift run)
- Subtle contextual explanation of delayed feedback dynamics.

---

### Task 4: Compilation, Docker Rebuild & DevTools Visual Verification

**Files:**
- None (build & verify)

- [x] **Step 1: Build Frontend**
Run: `npm --prefix frontend run build`
Expected: 0 errors.

- [x] **Step 2: Rebuild Docker Containers**
Run: `docker compose up --build -d react-frontend fastapi-engine`
Expected: Containers healthy.

- [x] **Step 3: Verify via Chrome DevTools MCP**
Navigate to `http://127.0.0.1:3000`, switch to `Drift & Stability` tab, take screenshots, test interactive "Run Retrospective Drift Analysis" button, and verify all visual components.

- [x] **Step 4: Run Full Regression Suite**
Run: `pytest tests/test_stream_api.py -v`
Expected: 100% passing.

---

### Task 5: State Documentation & Commit Proposal

**Files:**
- Modify: `memory.md`
- Modify: `decision.md`

- [x] **Step 1: Append decisions to `decision.md`**
- [x] **Step 2: Append steps to `memory.md`**
- [x] **Step 3: Explain changes to user before committing**

