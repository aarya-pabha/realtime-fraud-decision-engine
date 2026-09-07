# Design Specification: Dashboard Layout Reorganization & Sidebar Telemetry Cockpit

**Date:** 2026-09-07  
**Status:** Approved by User  
**Target Branch:** `feature/model-optimization-cost-sensitive`

---

## 1. Overview & Goals

This specification details the UX and layout reorganization of the main Dashboard and Sidebar:
1. **Vertical Hierarchy Correction:** Move `Decision Volume & Latency Analytics` (24h authorization bar chart) from the top of the middle grid down to the bottom of the page, where historical time-series analytics belong.
2. **Stream Forensics Shortening & In-Place Expandability:** Shorten `Recent Stream Forensics` from a tall 15-row list down to **3 rolling transactions** by default, with a clean `"View All (15)"` / `"Show Less"` toggle button.
3. **Reactive Forensics Station:** Rename `Active Policy Interventions` to **`Selected Transaction Forensics & Actions`**. When any transaction row is clicked in the stream, visibly highlight the selected row and trigger an attention glow on the forensics station so the user immediately sees the action and details.
4. **Pruning Redundant Cards:** Completely remove the `Dynamic Cost Router` card from the dashboard page.
5. **Sidebar Telemetry Cockpit:** Remove the basic "Engine Online" card in the left sidebar. Relocate and adapt `Real-Time Engine SLA` and `Top SHAP Risk Attribution Factors` into two clean, purpose-built panels within the left sidebar (`Sidebar.tsx`).

---

## 2. Dashboard Layout Specifications (`frontend/src/App.tsx`)

### 2.1 Page Flow (Top to Bottom)
1. **Header (`Header.tsx`):**
   - Retained: Single-row header with `Fraud Operations Console`, live SLA status pill, `+ Simulate Transaction`, and `Replay Stream`.
2. **Stat Cards Row (`StatCards.tsx`):**
   - Retained: 4 KPI Cards (Holdout Test Streamed, Direct Approvals, 3DS Challenges, Chargeback Ratio).
3. **Primary Operations Grid (2-Column):**
   - **Left Column (2/3 width):**
     - `StreamFeed.tsx`: Shows 3 rolling transactions by default with toggle button to expand to 15.
   - **Right Column (1/3 width):**
     - `PolicyActionBox.tsx`: Renamed to `Selected Transaction Forensics & Actions`, with reactive attention glow on selection.
     - `ProgressDonut.tsx`: `Dynamic Routing Distribution` radial donut chart.
4. **Secondary Analytics Row (Full Width):**
   - `AnalyticsChart.tsx`: `Decision Volume & Latency Analytics` (historical 24-hour authorization throughput and dynamic policy resolutions bar chart).
5. **Removed Cards:**
   - `Dynamic Cost Router` card is completely removed.
   - `Top SHAP Risk Attribution Factors` and `Real-Time Engine SLA` cards are removed from the bottom grid and moved into `Sidebar.tsx`.

---

## 3. Sidebar Telemetry Cockpit (`frontend/src/components/Sidebar.tsx`)

The sidebar (`w-64 bg-[#f8f9f5]`) will house:
1. **Brand Header:** `FraudEngine / DECISION PLATFORM` with green shield mark.
2. **Menu Navigation:** `Dashboard` (Live), `3DS Simulator` (Sandbox), `Drift & Stability` (Evidently).
3. **Telemetry Cockpit Stack (Bottom Section):**
   - **Card A: Real-Time Engine SLA:**
     - High-contrast obsidian card (`bg-[#111827] text-white p-3.5 rounded-xl border border-[#1f2937]`).
     - Header: `Engine SLA` with live green pulse dot and badge `p95 < 25ms`.
     - Large Latency Display: `avg_latency_ms` (e.g. `24.11 ms`).
     - Subtitle: `Single-pass LightGBM + TreeSHAP`.
   - **Card B: Top Risk Drivers (TreeSHAP):**
     - Clean white card (`bg-white border border-[#e9ebe3] p-3.5 rounded-xl`).
     - Header: `Top Risk Drivers` with badge `TreeSHAP`.
     - Compact ranking of top 4 global feature attributions:
       1. `Transaction Amount` (`+0.41`)
       2. `5-Min Card Velocity` (`+0.38`)
       3. `Disposable Email Domain` (`+0.29`)
       4. `Card Registration Tenancy` (`+0.22`)

---

## 4. Stream Forensics Shortening & Reactive Feedback (`frontend/src/components/StreamFeed.tsx`)

### 4.1 State & Display
- State: `isExpanded: boolean` (default `false`).
- Display slice: `isExpanded ? transactions : transactions.slice(0, 3)`.
- Toggle button: At the bottom of `StreamFeed`, render an expand/collapse button:
  - When collapsed: `View All Stream (${transactions.length}) ↓`
  - When expanded: `Show Recent 3 ↑`
- Hover & Active States:
  - Unselected: `bg-white border-transparent hover:bg-[#f8f9f5] hover:border-[#e9ebe3]`.
  - Selected: `bg-[#f3fbf5] border-[#006323] ring-1 ring-[#006323]/20 shadow-xs`.

---

## 5. Renamed Forensics Action Station (`frontend/src/components/PolicyActionBox.tsx`)

- Card Heading: **`Selected Transaction Forensics & Actions`**.
- Subtitle: `Inspect localized TreeSHAP factors, trigger manual 3DS challenges, or submit ground-truth dispute labels.`
- Attention Glow: Added `animate-pulse` or temporary highlight border (`border-[#006323] ring-2 ring-[#006323]/20`) when a new transaction is selected so user visual feedback is instant.
- Retains:
  - Transaction ID, dollar amount, fraud probability, card token.
  - Primary factor attribution tag.
  - `Trigger 3DS Step-Up Challenge` button.
  - Analyst Ground-Truth Feedback Station (`Flag Dispute` / `Mark Legit` writing to `feedback_store.sqlite`).

---

## 6. Verification Plan

1. **TypeScript Build:** `npm run build` in `frontend/` (0 errors).
2. **Container Rebuild:** `docker compose up --build -d react-frontend`.
3. **Visual Inspection:** Verify via Chrome DevTools MCP on `http://127.0.0.1:3000`:
   - Confirm sidebar contains SLA latency card and Top Risk Drivers.
   - Confirm stream displays 3 transactions rolling with toggle button.
   - Confirm clicking a transaction visibly updates and highlights the Forensics station.
   - Confirm bar chart sits below the stream.
   - Confirm `Dynamic Cost Router` card is gone.
