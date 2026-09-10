# Frontend Console Redesign & Brand Harmonization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign and harmonize the React frontend console to remove Donezo template placeholders ("Tasko", "Jessin Sam", search bar, mail/bell icons, General section), unify the pill & badge design system across all 3 pages, and decompose the application into modular view components.

**Architecture:** Create reusable `StatusPill.tsx` supporting semantic variants (`success`, `warning`, `danger`, `neutral`, `info`) with fine tone-on-tone borders and rounded-full geometry. Streamline `Header.tsx` into a single-row status-aware action bar. Prune `Sidebar.tsx` down to the 3 core tabs with modernized FinTech shield branding. Extract Tab 2 into `SimulatorView.tsx` and Tab 3 into `DriftView.tsx`. Refactor `App.tsx` into a lean orchestrator. Update HTML metadata.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Lucide React, Recharts, Vite, Docker Compose.

---

### Task 1: Create Reusable `StatusPill` Component

**Files:**
- Create: `frontend/src/components/StatusPill.tsx`

- [ ] **Step 1: Write `StatusPill.tsx` implementation**

```tsx
import React from 'react';

export type PillVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'info';
export type PillSize = 'sm' | 'md';

interface StatusPillProps {
  variant?: PillVariant;
  children: React.ReactNode;
  icon?: React.ReactNode;
  pulse?: boolean;
  size?: PillSize;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  variant = 'neutral',
  children,
  icon,
  pulse = false,
  size = 'md',
  className = '',
}) => {
  const getVariantStyles = (v: PillVariant) => {
    switch (v) {
      case 'success':
        return 'bg-[#e6f7ec] text-[#006323] border-[#a7f3d0]';
      case 'warning':
        return 'bg-[#fef7e6] text-[#b45309] border-[#fde68a]';
      case 'danger':
        return 'bg-[#feecee] text-[#b91c1c] border-[#fecaca]';
      case 'info':
        return 'bg-[#e0f2fe] text-[#0369a1] border-[#bae6fd]';
      case 'neutral':
      default:
        return 'bg-[#f1f3ee] text-[#202318] border-[#e9ebe3]';
    }
  };

  const getSizeStyles = (s: PillSize) => {
    switch (s) {
      case 'sm':
        return 'text-[11px] px-2.5 py-0.5';
      case 'md':
      default:
        return 'text-xs px-3 py-1';
    }
  };

  const getPulseDotColor = (v: PillVariant) => {
    switch (v) {
      case 'success':
        return 'bg-[#006323]';
      case 'warning':
        return 'bg-amber-500';
      case 'danger':
        return 'bg-rose-500';
      case 'info':
        return 'bg-sky-500';
      case 'neutral':
      default:
        return 'bg-[#707367]';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-bold border ${getVariantStyles(
        variant
      )} ${getSizeStyles(size)} ${className}`}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${getPulseDotColor(
              variant
            )} opacity-75`}
          />
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${getPulseDotColor(
              variant
            )}`}
          />
        </span>
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend; npm run build`  
Expected: Clean build without errors.

- [ ] **Step 3: Commit Task 1**

```bash
git add frontend/src/components/StatusPill.tsx
git commit -m "feat(ui): add reusable StatusPill component with soft semantic variants"
```

---

### Task 2: Streamline `Header.tsx` (Remove Dummy Placeholders)

**Files:**
- Modify: `frontend/src/components/Header.tsx`

- [ ] **Step 1: Refactor `Header.tsx` into a clean single-row header**

Replace entire content of `frontend/src/components/Header.tsx`:

```tsx
import React from 'react';
import { Plus, PlayCircle, ShieldCheck } from 'lucide-react';
import { StatusPill } from './StatusPill';

interface HeaderProps {
  onOpenScenarioModal: () => void;
  onRefreshStream: () => void;
  isStreaming: boolean;
}

export const Header: React.FC<HeaderProps> = ({ 
  onOpenScenarioModal, 
  onRefreshStream,
  isStreaming 
}) => {
  return (
    <header className="mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2">
        {/* Title & Live Status */}
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl lg:text-3xl font-extrabold text-[#202318] tracking-tight">
              Fraud Operations Console
            </h1>
            <StatusPill variant="success" pulse size="sm" icon={<ShieldCheck className="w-3.5 h-3.5" />}>
              Live Stream Active • Sub-25ms SLA
            </StatusPill>
          </div>
          <p className="text-xs lg:text-sm text-[#707367] mt-1 font-medium">
            Real-time Bayesian decisioning, online feature hydration & drift telemetry.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={onOpenScenarioModal}
            className="h-10 px-4 rounded-xl bg-[#006323] text-white text-sm font-bold flex items-center gap-2 shadow-md hover:bg-[#004d1b] hover:scale-102 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Simulate Transaction</span>
          </button>

          <button
            onClick={onRefreshStream}
            className="h-10 px-4 rounded-xl border border-[#e9ebe3] bg-white hover:bg-[#f1f3ee] text-[#202318] text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-xs"
          >
            <PlayCircle className={`w-4 h-4 ${isStreaming ? 'text-[#006323]' : 'text-amber-500'}`} />
            <span>{isStreaming ? 'Replay Stream' : 'Stream Paused'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend; npm run build`  
Expected: Clean build without errors.

- [ ] **Step 3: Commit Task 2**

```bash
git add frontend/src/components/Header.tsx
git commit -m "refactor(ui): streamline header to single row and remove dummy search and profile widgets"
```

---

### Task 3: Modernize & Prune `Sidebar.tsx`

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Refactor `Sidebar.tsx` to remove General section and update branding**

Replace entire content of `frontend/src/components/Sidebar.tsx`:

```tsx
import React from 'react';
import { 
  LayoutDashboard, 
  SquareCheckBig, 
  ShieldAlert, 
  ShieldCheck
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  streamOnline: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, streamOnline }) => {
  return (
    <aside className="w-64 bg-[#f8f9f5] border-r border-[#e9ebe3] p-5 h-screen flex flex-col justify-between fixed top-0 left-0 z-30 select-none">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3 mb-8 px-1">
          <div className="w-9 h-9 rounded-xl bg-[#006323] flex items-center justify-center text-white shadow-sm shadow-[#006323]/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="leading-tight">
            <span className="text-lg font-extrabold text-[#202318] tracking-tight block">
              FraudEngine
            </span>
            <span className="text-[10px] font-bold text-[#006323] tracking-wide uppercase block">
              Decision Platform
            </span>
          </div>
        </div>

        {/* Menu Section */}
        <div>
          <p className="text-[10px] font-bold text-[#707367] uppercase tracking-wider mb-2.5 px-3">
            Menu
          </p>
          <nav className="flex flex-col gap-1.5">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'dashboard'
                  ? 'bg-[#006323] text-white shadow-lg shadow-[#006323]/25 font-bold'
                  : 'text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeTab === 'dashboard' ? 'bg-white/20 text-white' : 'bg-[#e6f7ec] text-[#006323]'
              }`}>
                Live
              </span>
            </button>

            <button
              onClick={() => setActiveTab('simulator')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'simulator'
                  ? 'bg-[#006323] text-white shadow-lg shadow-[#006323]/25 font-bold'
                  : 'text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <SquareCheckBig className="w-4 h-4" />
                <span>3DS Simulator</span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeTab === 'simulator' ? 'bg-white/20 text-white' : 'bg-[#f1f3ee] text-[#707367]'
              }`}>
                Sandbox
              </span>
            </button>

            <button
              onClick={() => setActiveTab('drift')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'drift'
                  ? 'bg-[#006323] text-white shadow-lg shadow-[#006323]/25 font-bold'
                  : 'text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-4 h-4" />
                <span>Drift & Stability</span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeTab === 'drift' ? 'bg-white/20 text-white' : 'bg-[#f1f3ee] text-[#707367]'
              }`}>
                Evidently
              </span>
            </button>
          </nav>
        </div>
      </div>

      {/* Bottom Health Status Widget */}
      <div className="bg-white border border-[#e9ebe3] rounded-2xl p-4 shadow-xs">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${streamOnline ? 'bg-[#006323]' : 'bg-amber-500'} opacity-75`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${streamOnline ? 'bg-[#006323]' : 'bg-amber-500'}`} />
          </span>
          <span className="text-[11px] font-extrabold text-[#006323] uppercase tracking-wider">
            {streamOnline ? 'Engine Online' : 'Connecting...'}
          </span>
        </div>
        <p className="text-xs font-semibold text-[#202318] mb-0.5">LightGBM + TreeSHAP Active</p>
        <p className="text-[10px] text-[#707367] font-medium">Sub-25ms SLA Operational</p>
      </div>
    </aside>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend; npm run build`  
Expected: Clean build without errors.

- [ ] **Step 3: Commit Task 3**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "refactor(ui): update sidebar branding to FraudEngine and remove General section"
```

---

### Task 4: Extract and Polish `SimulatorView.tsx` (Tab 2)

**Files:**
- Create: `frontend/src/components/SimulatorView.tsx`

- [ ] **Step 1: Write `SimulatorView.tsx` with unified `StatusPill` integration**

```tsx
import React from 'react';
import { ShieldCheck, AlertTriangle, ShieldX, Clock, DollarSign, Activity } from 'lucide-react';
import { StatusPill } from './StatusPill';
import type { SimulationResult } from '../types';

interface SimulatorViewProps {
  selectedTx: SimulationResult | null;
  onSimulatePreset: (preset: 'attack' | 'highval' | 'normal') => void;
  onCustomSimulate: (payload: Record<string, unknown>) => void;
}

export const SimulatorView: React.FC<SimulatorViewProps> = ({
  selectedTx,
  onSimulatePreset,
}) => {
  return (
    <div className="space-y-6">
      <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="text-xl font-bold text-[#202318]">
              Interactive 3DS Decisioning Sandbox
            </h2>
            <p className="text-xs text-[#707367] mt-0.5">
              Test how the Bayesian Cost Router dynamically shifts decision boundaries based on transaction value and velocity.
            </p>
          </div>
          <StatusPill variant="info" size="sm">
            Three-Way Routing
          </StatusPill>
        </div>

        {/* Attack & Baseline Presets */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-6">
          <button
            onClick={() => onSimulatePreset('attack')}
            className="p-4 rounded-2xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-rose-50/50 hover:border-rose-200 text-left transition-all cursor-pointer group shadow-xs"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#202318] group-hover:text-rose-900 transition-colors">
                Velocity Burst Attack
              </span>
              <StatusPill variant="danger" size="sm">
                Hard Decline
              </StatusPill>
            </div>
            <p className="text-xs text-[#707367] font-medium">
              $45.00 • 8 tx / 5m • Disposable Email
            </p>
            <p className="text-[10px] text-rose-600 font-semibold mt-2">
              Triggers card velocity defense
            </p>
          </button>

          <button
            onClick={() => onSimulatePreset('highval')}
            className="p-4 rounded-2xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-amber-50/50 hover:border-amber-200 text-left transition-all cursor-pointer group shadow-xs"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#202318] group-hover:text-amber-900 transition-colors">
                High-Value Tech Order
              </span>
              <StatusPill variant="warning" size="sm">
                Dynamic 3DS
              </StatusPill>
            </div>
            <p className="text-xs text-[#707367] font-medium">
              $2,400.00 • 1 tx / 5m • Electronics
            </p>
            <p className="text-[10px] text-amber-700 font-semibold mt-2">
              Asymmetric low-cost challenge buffer
            </p>
          </button>

          <button
            onClick={() => onSimulatePreset('normal')}
            className="p-4 rounded-2xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-emerald-50/50 hover:border-emerald-200 text-left transition-all cursor-pointer group shadow-xs"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#202318] group-hover:text-emerald-900 transition-colors">
                Baseline Retail Order
              </span>
              <StatusPill variant="success" size="sm">
                Direct Approval
              </StatusPill>
            </div>
            <p className="text-xs text-[#707367] font-medium">
              $25.00 • 1 tx / 5m • Domestic Retail
            </p>
            <p className="text-[10px] text-[#006323] font-semibold mt-2">
              0% friction • $0.00 authorization cost
            </p>
          </button>
        </div>

        {/* Latest Simulation Result */}
        {selectedTx && (
          <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
              <div>
                <span className="text-xs font-bold text-[#707367] uppercase tracking-wide">
                  Latest Simulation Decision
                </span>
                <div className="flex items-center gap-3 mt-1">
                  <h3 className="text-2xl font-black text-[#202318]">
                    {selectedTx.action === 'APPROVE' && 'Direct Approval'}
                    {selectedTx.action === 'STEP_UP_3DS' && 'Dynamic 3DS Challenge'}
                    {selectedTx.action === 'DECLINE' && 'Hard Fraud Decline'}
                  </h3>
                  {selectedTx.action === 'APPROVE' && (
                    <StatusPill variant="success" icon={<ShieldCheck className="w-3.5 h-3.5" />}>
                      Approved
                    </StatusPill>
                  )}
                  {selectedTx.action === 'STEP_UP_3DS' && (
                    <StatusPill variant="warning" icon={<AlertTriangle className="w-3.5 h-3.5" />}>
                      Step-Up 3DS2
                    </StatusPill>
                  )}
                  {selectedTx.action === 'DECLINE' && (
                    <StatusPill variant="danger" icon={<ShieldX className="w-3.5 h-3.5" />}>
                      Declined
                    </StatusPill>
                  )}
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs text-[#707367] flex items-center justify-end gap-1">
                  <Clock className="w-3 h-3 text-[#006323]" />
                  Execution Latency
                </span>
                <p className="text-xl font-bold text-[#006323] mono-num">
                  {selectedTx.total_latency_ms.toFixed(2)} ms
                </p>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-4">
              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[#707367] flex items-center gap-1 mb-1">
                  <DollarSign className="w-3 h-3" />
                  Transaction Amount
                </span>
                <span className="text-sm font-bold text-[#202318] mono-num">
                  ${selectedTx.transaction_amount.toFixed(2)}
                </span>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[#707367] flex items-center gap-1 mb-1">
                  <Activity className="w-3 h-3" />
                  P(Fraud) Score
                </span>
                <span className="text-sm font-bold text-[#202318] mono-num">
                  {(selectedTx.fraud_probability * 100).toFixed(2)}%
                </span>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[#707367] block mb-1">
                  Step-Up Threshold τ*
                </span>
                <span className="text-sm font-bold text-amber-700 mono-num">
                  {selectedTx.tau_step_up ? selectedTx.tau_step_up.toFixed(3) : '0.045'}
                </span>
              </div>
              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[#707367] block mb-1">
                  Decline Threshold k·τ*
                </span>
                <span className="text-sm font-bold text-rose-700 mono-num">
                  {selectedTx.tau_decline ? selectedTx.tau_decline.toFixed(3) : '0.180'}
                </span>
              </div>
            </div>

            {/* Top Localized TreeSHAP Reason Codes */}
            <div className="bg-white p-4 rounded-xl border border-[#e9ebe3] shadow-xs">
              <span className="text-xs font-bold text-[#707367] uppercase tracking-wide block mb-2.5">
                Top Localized TreeSHAP Attribution Codes
              </span>
              <div className="flex flex-wrap gap-2">
                {selectedTx.reason_codes && selectedTx.reason_codes.length > 0 ? (
                  selectedTx.reason_codes.map((rc, idx) => (
                    <StatusPill
                      key={idx}
                      variant={
                        selectedTx.action === 'DECLINE'
                          ? 'danger'
                          : selectedTx.action === 'STEP_UP_3DS'
                          ? 'warning'
                          : 'neutral'
                      }
                      size="sm"
                    >
                      {rc}
                    </StatusPill>
                  ))
                ) : (
                  <StatusPill variant="success" size="sm" icon={<ShieldCheck className="w-3 h-3" />}>
                    Baseline Normal Transaction (Zero Risk Signals)
                  </StatusPill>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend; npm run build`  
Expected: Clean build without errors.

- [ ] **Step 3: Commit Task 4**

```bash
git add frontend/src/components/SimulatorView.tsx
git commit -m "feat(ui): extract SimulatorView with unified StatusPill badges and card presets"
```

---

### Task 5: Extract and Polish `DriftView.tsx` (Tab 3)

**Files:**
- Create: `frontend/src/components/DriftView.tsx`

- [ ] **Step 1: Write `DriftView.tsx` with unified `StatusPill` integration**

```tsx
import React from 'react';
import { ShieldCheck, Database, BarChart2 } from 'lucide-react';
import { StatusPill } from './StatusPill';

export const DriftView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-bold text-[#202318] tracking-tight">
              Evidently AI Stability & Concept Drift Center
            </h2>
            <p className="text-xs text-[#707367] mt-0.5">
              Monitors distribution shifts across payment amounts, burst velocities, and delayed ground-truth chargebacks.
            </p>
          </div>
          <StatusPill variant="success" pulse icon={<ShieldCheck className="w-3.5 h-3.5" />}>
            Model Stable • 0 Alerts
          </StatusPill>
        </div>

        {/* Drift Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#707367] font-bold uppercase tracking-wider">
                Transaction Amount Drift
              </span>
              <StatusPill variant="success" size="sm">
                Safe
              </StatusPill>
            </div>
            <p className="text-3xl font-extrabold text-[#202318] mt-1 mono-num">0.038</p>
            <div className="mt-3 pt-3 border-t border-[#e9ebe3]">
              <StatusPill variant="success" size="sm">
                Wasserstein Distance &lt; 0.10 Threshold
              </StatusPill>
            </div>
          </div>

          <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#707367] font-bold uppercase tracking-wider">
                Velocity 5m Drift
              </span>
              <StatusPill variant="success" size="sm">
                Safe
              </StatusPill>
            </div>
            <p className="text-3xl font-extrabold text-[#202318] mt-1 mono-num">0.021</p>
            <div className="mt-3 pt-3 border-t border-[#e9ebe3]">
              <StatusPill variant="success" size="sm">
                Jensen-Shannon Divergence Safe
              </StatusPill>
            </div>
          </div>

          <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#707367] font-bold uppercase tracking-wider">
                Prediction Drift (PR-AUC)
              </span>
              <StatusPill variant="success" size="sm">
                Stable
              </StatusPill>
            </div>
            <p className="text-3xl font-extrabold text-[#202318] mt-1 mono-num">0.506</p>
            <div className="mt-3 pt-3 border-t border-[#e9ebe3]">
              <StatusPill variant="success" size="sm">
                Within ±2.0% Tolerance of Baseline
              </StatusPill>
            </div>
          </div>
        </div>

        {/* Delayed Feedback Buffer Station */}
        <div className="border border-[#e9ebe3] rounded-2xl p-5 bg-[#f8f9f5] shadow-xs">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-[#006323]" />
            <h4 className="text-xs font-bold text-[#202318] uppercase tracking-wide">
              Delayed Feedback Dispute Buffer (SQLite)
            </h4>
          </div>
          <p className="text-xs text-[#707367] leading-relaxed">
            Analyst dispute labels are committed to <code className="bg-white px-2 py-0.5 rounded-md text-[11px] font-bold text-[#202318] border border-[#e9ebe3]">data/feedback_store.sqlite</code> and buffered for retrospective drift computation over 120-day horizons, preventing feedback loops from degrading calibrated probabilities.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <StatusPill variant="info" size="sm" icon={<BarChart2 className="w-3 h-3" />}>
              120-Day Label Window
            </StatusPill>
            <StatusPill variant="neutral" size="sm">
              Non-Blocking Hydration
            </StatusPill>
          </div>
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend; npm run build`  
Expected: Clean build without errors.

- [ ] **Step 3: Commit Task 5**

```bash
git add frontend/src/components/DriftView.tsx
git commit -m "feat(ui): extract DriftView with unified StatusPill badges and metric cards"
```

---

### Task 6: Decompose `App.tsx` & Update Platform Metadata

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/index.html`

- [ ] **Step 1: Update `frontend/index.html` title**

Change line 8:
```html
<title>Real-Time Transaction Fraud Engine</title>
```

- [ ] **Step 2: Refactor `frontend/src/App.tsx`**

Integrate `<SimulatorView />` and `<DriftView />`, removing lines 200–363.

- [ ] **Step 3: Verify TypeScript compilation and bundling**

Run: `cd frontend; npm run build`  
Expected: Clean build with Vite in <3s and zero warnings.

- [ ] **Step 4: Commit Task 6**

```bash
git add frontend/src/App.tsx frontend/index.html
git commit -m "refactor(ui): decompose App.tsx into dedicated views and update document title"
```

---

### Task 7: Container Deployment & Visual Verification

**Files:**
- Container: `fraud-frontend` (`docker/Dockerfile.frontend`)

- [ ] **Step 1: Rebuild and deploy container**

Run: `docker compose up --build -d fraud-frontend`  
Expected: Successful container build and restart.

- [ ] **Step 2: Inspect live UI via Chrome DevTools MCP**

Navigate to `http://127.0.0.1:3000`.  
Capture screenshots of:
1. Dashboard View
2. 3DS Simulator View
3. Drift & Stability View

Verify:
- "Tasko" branding is completely gone.
- Search bar `⌘F`, mail, bell, and Jessin Sam profile are gone.
- Sidebar "GENERAL" section is gone.
- All pills across all 3 pages use the unified `StatusPill` design.

- [ ] **Step 3: Run backend regression suite**

Run: `pytest tests/test_stream_api.py -v`  
Expected: 100% passing tests.

- [ ] **Step 4: Commit and finalize**

```bash
git status -s
```
Verify 100% clean working directory.
