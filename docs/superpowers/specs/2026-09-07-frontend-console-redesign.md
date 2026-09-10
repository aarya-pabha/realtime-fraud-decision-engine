# Design Specification: Frontend Console Redesign & Brand Harmonization

**Date:** 2026-09-07  
**Status:** Approved by User  
**Target Branch:** `feature/model-optimization-cost-sensitive`

---

## 1. Executive Summary & Goals

This specification details the comprehensive visual and structural redesign of the React frontend application (`frontend/`). The goals are:
1. **Brand Identity Unification:** Completely eliminate template placeholder branding ("Tasko FraudOps", "Tasko Dashboard", "JS Jessin Sam") and establish the canonical platform identity: **Real-Time Transaction Fraud Engine**.
2. **Top Header Simplification:** Remove all non-functional Donezo template widgets (the search bar `⌘F`, mail button, notification bell with red dot, and user profile avatar). Transition to a clean, high-contrast single-row header featuring console title, live stream status pill, and primary operational actions (`+ Simulate Transaction`, `Replay Stream`).
3. **Sidebar Cleanup:** Remove the "GENERAL" section and its dead links ("FastAPI Swagger Docs", "Engine Settings"). Focus the navigation purely on the 3 core operational tabs (`Dashboard`, `3DS Simulator`, `Drift & Stability`) with a modernized brand emblem and the live engine health status card.
4. **Pill & Badge Design System Harmonization:** Replace ad-hoc, boxy, or raw-text statuses on the secondary tabs (`3DS Simulator` and `Drift & Stability`) with a reusable `StatusPill` component that strictly adheres to the rounded-full, soft-tinted, fine-bordered design system from the main Dashboard.
5. **Modular Component Decomposition:** Extract Tab 2 and Tab 3 out of the monolithic `App.tsx` into dedicated, self-contained view components (`SimulatorView.tsx`, `DriftView.tsx`), reducing `App.tsx` size by >60% and improving testability and maintainability.

---

## 2. Platform Branding & Meta Specifications

- **Application Title:** `Real-Time Transaction Fraud Engine`
- **Subtitle:** `Real-time Bayesian decisioning, online feature hydration & drift telemetry.`
- **HTML Document Title (`frontend/index.html`):** Update from `<title>Tasko Dashboard</title>` to `<title>Real-Time Transaction Fraud Engine</title>`.
- **Primary Visual Theme:**
  - Canvas: `#f8f9f5`
  - Primary FinTech Green: `#006323` (Hover: `#004d1b`, Accent/Pill: `#e6f7ec`)
  - Dark Typography: `#202318`
  - Subtext Typography: `#707367`
  - Card Surface: `#ffffff`
  - Borders: `#e9ebe3`
  - Card Radius: `rounded-2xl` (16-20px)
  - Badge / Pill Radius: `rounded-full` (9999px)

---

## 3. Header Architecture (`frontend/src/components/Header.tsx`)

### 3.1 Elements Removed
- The top utility row (lines 18–60) is completely deleted:
  - Search input with `⌘F` keyboard badge.
  - Mail icon button.
  - Bell icon button with red pulsing indicator.
  - User avatar and profile info (`JS Jessin Sam / Risk Operations Lead`).

### 3.2 Elements Retained & Upgraded
- **Single-Row Layout:** A spacious, responsive flex container (`flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2`).
- **Left Column:**
  - Platform Title: `Fraud Operations Console` (`text-2xl lg:text-3xl font-extrabold text-[#202318] tracking-tight`).
  - Subtitle: `Real-time Bayesian decisioning, online feature hydration & drift telemetry.` (`text-xs lg:text-sm text-[#707367] mt-0.5 font-medium`).
  - Live Status Pill inline with title: A soft emerald pill (`bg-[#e6f7ec] text-[#006323] border border-[#a7f3d0] rounded-full px-3 py-0.5 text-xs font-bold inline-flex items-center gap-1.5`) showing a pulsing dot and `Live Stream Active • Sub-25ms SLA`.
- **Right Column (Action Buttons):**
  - Primary Action: `+ Simulate Transaction` (`bg-[#006323] hover:bg-[#004d1b] text-white font-bold text-sm h-10 px-4 rounded-xl shadow-md flex items-center gap-2`).
  - Secondary Action: `Replay Stream` / `Stream Paused` (`bg-white hover:bg-[#f1f3ee] border border-[#e9ebe3] text-[#202318] font-semibold text-sm h-10 px-4 rounded-xl flex items-center gap-2 shadow-xs`).

---

## 4. Sidebar Architecture (`frontend/src/components/Sidebar.tsx`)

### 4.1 Brand Header
- Replace the Tasko smiley face logo with a FinTech shield emblem (`Shield` or geometric lock badge in `#006323` circle).
- Update brand text:
  - Header: `FraudEngine`
  - Subtitle: `Decision Platform` (in `text-[11px] font-bold text-[#006323]`).

### 4.2 Navigation Menu
- Header: `MENU` (`text-[10px] font-bold text-[#707367] uppercase tracking-wider`).
- 3 Active Tabs:
  1. `Dashboard` (`LayoutDashboard` icon): Pill badge `Live` (`bg-[#e6f7ec] text-[#006323]` when inactive; `bg-white/20 text-white` when active).
  2. `3DS Simulator` (`SquareCheckBig` icon): Pill badge `Sandbox` (unified `rounded-full` styling).
  3. `Drift & Stability` (`ShieldAlert` icon): Pill badge `Evidently` (unified `rounded-full` styling).

### 4.3 Removed Sections
- Entire "GENERAL" section removed (including "FastAPI Swagger Docs" and "Engine Settings").

### 4.4 Bottom Engine Status Widget
- Retained: High-contrast white card (`border border-[#e9ebe3] rounded-2xl p-4`) with pulsing status dot (`Engine Online`), model status (`LightGBM + TreeSHAP Active`), and SLA latency assurance (`Sub-25ms SLA Operational`).

---

## 5. Unified Pill & Badge Component (`frontend/src/components/StatusPill.tsx`)

Create a reusable component encapsulating semantic color tokens, borders, and geometry:

```tsx
export type PillVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'info';
export type PillSize = 'sm' | 'md';

interface StatusPillProps {
  variant: PillVariant;
  children: React.ReactNode;
  icon?: React.ReactNode;
  pulse?: boolean;
  size?: PillSize;
  className?: string;
}
```

### 5.1 Variant Styling Map
- `success` (Approved / Safe / Stable):
  `bg-[#e6f7ec] text-[#006323] border border-[#a7f3d0]`
- `warning` (3DS Step-Up / Challenge / Drift Alert):
  `bg-[#fef7e6] text-[#b45309] border border-[#fde68a]`
- `danger` (Decline / High Risk / Violation):
  `bg-[#feecee] text-[#b91c1c] border border-[#fecaca]`
- `neutral` (SHAP Reason / Telemetry / Attribute):
  `bg-[#f1f3ee] text-[#202318] border border-[#e9ebe3]`
- `info` (Metadata / Protocol / Version):
  `bg-[#e0f2fe] text-[#0369a1] border border-[#bae6fd]`

All variants enforce `rounded-full font-bold inline-flex items-center gap-1.5`.

---

## 6. Simulator View Refactoring (`frontend/src/components/SimulatorView.tsx`)

Extract Tab 2 into `SimulatorView.tsx`.
- **Preset Cards:** 3 cards (`Velocity Burst`, `High-Value Tech`, `Baseline Retail`). Each card features:
  - Preset title and subtitle ($ amount, velocity, channel).
  - Status chip using `StatusPill`:
    - Velocity Burst: `danger` -> `Hard Decline`
    - High-Value Tech: `warning` -> `Dynamic 3DS Challenge`
    - Baseline Retail: `success` -> `Direct Approval`
- **Latest Simulation Result:**
  - Verdict Banner: Large heading accompanied by `StatusPill` with matching icon (`ShieldCheck`, `AlertTriangle`, `ShieldX`).
  - Latency display: `selectedTx.total_latency_ms` with `mono-num text-[#006323]`.
  - Metrics Grid: 4 cards for Transaction Amount, P(Fraud) Score, Step-Up Threshold $\tau^*$, Decline Threshold $k \cdot \tau^*$.
  - Reason Codes: TreeSHAP features rendered using `StatusPill` variant `neutral` or `warning` instead of plain square `rounded-lg` tags.

---

## 7. Drift Center Refactoring (`frontend/src/components/DriftView.tsx`)

Extract Tab 3 into `DriftView.tsx`.
- **Header Badge:** `StatusPill` variant `success` with green pulse dot: `Model Stable • 0 Alerts`.
- **Metric Cards:** 3 drift KPI cards (Amount Drift, Velocity Drift, Prediction Drift PR-AUC).
  - Replaces raw paragraphs with `StatusPill` components:
    - Amount Drift: `StatusPill variant="success"` -> `Wasserstein Safe (< 0.10)`
    - Velocity Drift: `StatusPill variant="success"` -> `Jensen-Shannon Safe`
    - Prediction Drift: `StatusPill variant="success"` -> `Within ±2.0% Tolerance`
- **Delayed Feedback Buffer Card:** Clean information panel for SQLite feedback queue.

---

## 8. App Orchestrator Simplification (`frontend/src/App.tsx`)

Refactor `App.tsx`:
- Imports: `Sidebar`, `Header`, `StatCards`, `AnalyticsChart`, `PolicyActionBox`, `ProgressDonut`, `StreamFeed`, `RiskDrivers`, `TelemetryCards`, `ScenarioModal`, `SimulatorView`, `DriftView`.
- Cleans up duplicate inline JSX for Tabs 2 & 3.
- Conditionally renders:
  - `activeTab === 'dashboard'` -> Main analytics grid and live forensic stream.
  - `activeTab === 'simulator'` -> `<SimulatorView ... />`
  - `activeTab === 'drift'` -> `<DriftView ... />`

---

## 9. Verification & Validation Plan

1. **TypeScript & Build Verification:**
   - Execute `npm run build` inside `frontend/` to verify zero type errors, clean Vite bundling, and valid asset imports.
2. **Visual Inspection:**
   - Verify live frontend rendering via Chrome DevTools MCP on `http://127.0.0.1:3000`.
   - Take screenshots of all 3 tabs (Dashboard, 3DS Simulator, Drift & Stability).
   - Confirm complete absence of "Tasko", "Jessin Sam", search bar, mail/bell icons, and "General" section.
   - Confirm unified rounded-full pill styling across all tabs.
3. **Backend Integration & Regression:**
   - Ensure the simulation endpoints (`POST /v1/stream/simulate`) and stream polling continue to function seamlessly.
   - Run backend pytest regression suite (`pytest`) to guarantee zero backend regression.
