# Dashboard Layout Reorganization & Sidebar Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the Dashboard page to place historical analytics at the bottom, shorten Stream Forensics to 3 rolling transactions with an expand toggle, make the Selected Transaction Forensics card visibly reactive on click, remove the Dynamic Cost Router card, and shift Real-Time SLA and Top SHAP Risk Drivers into the left sidebar.

**Architecture:** Update `Sidebar.tsx` to incorporate a dual-card Telemetry Cockpit (dark Engine SLA card + Top Risk Drivers card) and remove the basic Engine Online box. Update `StreamFeed.tsx` to default to 3 transactions with a toggle button to expand to 15. Update `PolicyActionBox.tsx` to "Selected Transaction Forensics & Actions" with a selection glow effect. Restructure `App.tsx` grid: Stat Cards -> Stream & Actions -> Decision Volume Bar Chart, while pruning the removed cards.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Lucide React, Recharts, Vite, Docker Compose.

---

### Task 1: Add Telemetry Cockpit to Sidebar (`frontend/src/components/Sidebar.tsx`)

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Update `Sidebar.tsx` with SLA card and Top Risk Drivers**

```tsx
import React from 'react';
import { 
  LayoutDashboard, 
  SquareCheckBig, 
  ShieldAlert, 
  ShieldCheck,
  Zap
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  streamOnline: boolean;
  avgLatencyMs?: number;
  p95LatencyMs?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  activeTab, 
  setActiveTab, 
  streamOnline,
  avgLatencyMs = 24.11,
  p95LatencyMs = 23.46,
}) => {
  return (
    <aside className="w-64 bg-[#f8f9f5] border-r border-[#e9ebe3] p-5 h-screen flex flex-col justify-between fixed top-0 left-0 z-30 select-none overflow-y-auto">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3 mb-6 px-1">
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

        {/* Menu Navigation */}
        <div className="mb-6">
          <p className="text-[10px] font-bold text-[#707367] uppercase tracking-wider mb-2 px-3">
            Menu
          </p>
          <nav className="flex flex-col gap-1.5">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
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
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
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
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
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

      {/* Telemetry Cockpit Section */}
      <div className="flex flex-col gap-3 pt-3 border-t border-[#e9ebe3]">
        {/* Real-Time Engine SLA Card */}
        <div className="bg-[#111827] text-white rounded-xl p-3.5 border border-[#1f2937] shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${streamOnline ? 'bg-emerald-400' : 'bg-amber-400'} opacity-75`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${streamOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              </span>
              <span className="text-[10px] font-extrabold text-emerald-400 uppercase tracking-wider">
                Engine SLA
              </span>
            </div>
            <span className="text-[9px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full">
              p95 &lt; 25ms
            </span>
          </div>
          <div className="text-2xl font-black tracking-tight mono-num text-white my-1">
            {avgLatencyMs.toFixed(2)} <span className="text-xs font-normal text-gray-400">ms</span>
          </div>
          <p className="text-[10px] text-gray-400 font-medium">
            Single-pass LightGBM + TreeSHAP
          </p>
        </div>

        {/* Top Risk Drivers Card */}
        <div className="bg-white border border-[#e9ebe3] rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[10px] font-bold text-[#707367] uppercase tracking-wider flex items-center gap-1">
              <Zap className="w-3 h-3 text-[#006323]" />
              Top Risk Drivers
            </span>
            <span className="text-[9px] font-extrabold text-[#006323] bg-[#e6f7ec] px-1.5 py-0.5 rounded-md border border-[#a7f3d0]">
              TreeSHAP
            </span>
          </div>
          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">Transaction Amount</span>
              <span className="text-[10px] font-bold text-[#b45309] bg-[#fef7e6] border border-[#fde68a] px-1.5 py-0.2 rounded-full mono-num">+0.41</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">5m Card Velocity</span>
              <span className="text-[10px] font-bold text-[#b45309] bg-[#fef7e6] border border-[#fde68a] px-1.5 py-0.2 rounded-full mono-num">+0.38</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">Disposable Email</span>
              <span className="text-[10px] font-bold text-[#b91c1c] bg-[#feecee] border border-[#fecaca] px-1.5 py-0.2 rounded-full mono-num">+0.29</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">Account Tenancy</span>
              <span className="text-[10px] font-bold text-[#707367] bg-[#f1f3ee] border border-[#e9ebe3] px-1.5 py-0.2 rounded-full mono-num">+0.22</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `npm --prefix frontend run build`

- [ ] **Step 3: Commit Task 1**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat(ui): add real-time SLA telemetry and top SHAP risk drivers to sidebar"
```

---

### Task 2: Shorten Stream Forensics & Add Expand Toggle (`frontend/src/components/StreamFeed.tsx`)

**Files:**
- Modify: `frontend/src/components/StreamFeed.tsx`

- [ ] **Step 1: Update `StreamFeed.tsx` with 3-row limit and toggle button**

```tsx
import React, { useState } from 'react';
import { ChevronRight, ShieldCheck, AlertTriangle, ShieldX, ChevronDown, ChevronUp } from 'lucide-react';
import type { TransactionItem } from '../types';

interface StreamFeedProps {
  transactions: TransactionItem[];
  selectedTxId: number | null;
  onSelectTransaction: (tx: TransactionItem) => void;
}

export const StreamFeed: React.FC<StreamFeedProps> = ({
  transactions,
  selectedTxId,
  onSelectTransaction,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getActionChip = (action: string) => {
    switch (action) {
      case 'APPROVE':
        return (
          <span className="bg-[#e6f7ec] text-[#006323] text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 border border-[#a7f3d0]">
            <ShieldCheck className="w-3 h-3" />
            Approved
          </span>
        );
      case 'STEP_UP_3DS':
        return (
          <span className="bg-[#fef7e6] text-[#b45309] text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 border border-[#fde68a]">
            <AlertTriangle className="w-3 h-3" />
            3DS Step-Up
          </span>
        );
      case 'DECLINE':
      default:
        return (
          <span className="bg-[#feecee] text-[#b91c1c] text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 border border-[#fecaca]">
            <ShieldX className="w-3 h-3" />
            Declined
          </span>
        );
    }
  };

  const getAvatarInitials = (action: string) => {
    switch (action) {
      case 'APPROVE': return 'AP';
      case 'STEP_UP_3DS': return '3D';
      case 'DECLINE': return 'DC';
      default: return 'TX';
    }
  };

  const displayedTransactions = isExpanded ? transactions : transactions.slice(0, 3);

  return (
    <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-[#202318] tracking-tight">
            Recent Stream Forensics
          </h2>
          <p className="text-xs text-[#707367]">
            Click any row to inspect attribution and submit ground-truth chargeback feedback
          </p>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-8 px-3 rounded-lg border border-[#e9ebe3] text-xs font-semibold text-[#202318] hover:bg-[#f1f3ee] flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5 text-[#707367]" />
              <span>Show Recent 3</span>
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5 text-[#707367]" />
              <span>View All ({transactions.length})</span>
            </>
          )}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {transactions.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#707367]">
            Waiting for live transactions from Redpanda stream...
          </div>
        ) : (
          displayedTransactions.map((tx) => {
            const isSelected = selectedTxId === tx.transaction_id;
            return (
              <div
                key={tx.transaction_id}
                onClick={() => onSelectTransaction(tx)}
                className={`flex items-center justify-between p-3 rounded-xl transition-all duration-200 cursor-pointer border ${
                  isSelected
                    ? 'bg-[#f3fbf5] border-[#006323] ring-2 ring-[#006323]/20 shadow-xs'
                    : 'bg-white border-transparent hover:bg-[#f8f9f5] hover:border-[#e9ebe3]'
                }`}
              >
                {/* Left: Avatar & Metadata */}
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ring-2 ${
                    tx.action === 'APPROVE'
                      ? 'bg-[#e6f7ec] text-[#006323] ring-[#006323]/20'
                      : tx.action === 'STEP_UP_3DS'
                      ? 'bg-[#fef7e6] text-[#b45309] ring-amber-500/20'
                      : 'bg-[#feecee] text-[#b91c1c] ring-rose-500/20'
                  }`}>
                    {getAvatarInitials(tx.action)}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-[#202318] truncate">
                        ${tx.transaction_amount.toFixed(2)}
                      </p>
                      <span className="text-xs font-medium text-[#707367] mono-num">
                        • {tx.card_token}
                      </span>
                    </div>
                    <p className="text-xs text-[#707367] truncate mt-0.5">
                      P(Fraud): <span className="font-bold text-[#202318] mono-num">{(tx.fraud_probability * 100).toFixed(1)}%</span> • {tx.primary_reason}
                    </p>
                  </div>
                </div>

                {/* Right: Status Pill & Arrow */}
                <div className="flex items-center gap-3 shrink-0 ml-3">
                  {getActionChip(tx.action)}
                  <ChevronRight className={`w-4 h-4 text-[#707367] transition-transform ${isSelected ? 'rotate-90 text-[#006323]' : ''}`} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `npm --prefix frontend run build`

- [ ] **Step 3: Commit Task 2**

```bash
git add frontend/src/components/StreamFeed.tsx
git commit -m "feat(ui): shorten stream feed to 3 rolling transactions with expand toggle"
```

---

### Task 3: Rename & Enhance Forensics Action Box (`frontend/src/components/PolicyActionBox.tsx`)

**Files:**
- Modify: `frontend/src/components/PolicyActionBox.tsx`

- [ ] **Step 1: Update `PolicyActionBox.tsx` with new title and reactive selection feedback**

```tsx
import React, { useState, useEffect } from 'react';
import { AlertCircle, ShieldAlert, CheckCircle2, ShieldCheck, Target } from 'lucide-react';
import type { TransactionItem } from '../types';

interface PolicyActionBoxProps {
  selectedTx: TransactionItem | null;
  onSubmitFeedback: (txId: number, isChargeback: boolean) => Promise<void>;
}

export const PolicyActionBox: React.FC<PolicyActionBoxProps> = ({
  selectedTx,
  onSubmitFeedback,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [highlightKey, setHighlightKey] = useState<number | null>(null);

  // Trigger attention highlight when selectedTx changes
  useEffect(() => {
    if (selectedTx) {
      setHighlightKey(selectedTx.transaction_id);
      const timer = setTimeout(() => setHighlightKey(null), 1200);
      return () => clearTimeout(timer);
    }
  }, [selectedTx?.transaction_id]);

  const handleFeedback = async (isChargeback: boolean) => {
    if (!selectedTx) return;
    setSubmitting(true);
    try {
      await onSubmitFeedback(selectedTx.transaction_id, isChargeback);
      setFeedbackSuccess(isChargeback ? 'Flagged as Chargeback' : 'Confirmed Legitimate');
      setTimeout(() => setFeedbackSuccess(null), 3000);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`bg-white border rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300 ${
      highlightKey ? 'border-[#006323] ring-2 ring-[#006323]/20 shadow-md' : 'border-[#e9ebe3]'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold text-[#202318] tracking-tight flex items-center gap-2">
          <Target className="w-4 h-4 text-[#006323]" />
          Selected Transaction Forensics & Actions
        </h2>
      </div>

      {selectedTx ? (
        <div className="space-y-4">
          <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4 transition-all duration-300 hover:shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-[#006323] uppercase tracking-wider">
                Target Transaction #{selectedTx.transaction_id}
              </span>
              <span className="text-xs font-bold text-[#202318] mono-num">
                ${selectedTx.transaction_amount.toFixed(2)}
              </span>
            </div>

            <p className="text-xs text-[#707367] mb-3 font-medium">
              Risk Probability: <span className="font-bold text-[#202318] mono-num">{(selectedTx.fraud_probability * 100).toFixed(1)}%</span> • {selectedTx.card_token}
            </p>

            <div className="bg-white border border-[#e9ebe3] rounded-lg p-2.5 mb-3 text-xs text-[#202318]">
              <span className="font-bold text-[#707367] block text-[10px] uppercase tracking-wide mb-1">
                Primary Factor Attribution:
              </span>
              <p className="font-semibold text-[#006323]">
                {selectedTx.primary_reason}
              </p>
            </div>

            <button
              onClick={() => handleFeedback(true)}
              disabled={submitting}
              className="w-full h-10 rounded-xl bg-[#006323] text-white text-xs font-bold flex items-center justify-center gap-2 hover:bg-[#004d1b] transition-all shadow-md cursor-pointer disabled:opacity-50"
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Trigger 3DS Step-Up Challenge</span>
            </button>
          </div>

          {/* Dispute Feedback Loop */}
          <div className="pt-2">
            <p className="text-xs font-bold text-[#202318] mb-1">
              Analyst Ground-Truth Feedback Station
            </p>
            <p className="text-[11px] text-[#707367] mb-2.5">
              Submits verified chargeback labels to update Evidently AI stability distributions:
            </p>

            {feedbackSuccess && (
              <div className="mb-2.5 p-2 rounded-lg bg-[#e6f7ec] border border-[#a7f3d0] text-[#006323] text-xs font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{feedbackSuccess}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleFeedback(true)}
                disabled={submitting}
                className="h-9 rounded-xl border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
              >
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Flag Dispute</span>
              </button>

              <button
                onClick={() => handleFeedback(false)}
                disabled={submitting}
                className="h-9 rounded-xl border border-[#e9ebe3] bg-white hover:bg-[#f1f3ee] text-[#202318] text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-xs"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#006323]" />
                <span>Mark Legit</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 text-center bg-[#f8f9f5] rounded-xl border border-[#e9ebe3] text-xs text-[#707367]">
          Select any transaction from the stream table to inspect dynamic decision attributes and trigger policy interventions.
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `npm --prefix frontend run build`

- [ ] **Step 3: Commit Task 3**

```bash
git add frontend/src/components/PolicyActionBox.tsx
git commit -m "refactor(ui): rename to Selected Transaction Forensics & Actions with reactive selection glow"
```

---

### Task 4: Reorganize Dashboard Flow (`frontend/src/App.tsx`)

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update `App.tsx` to move bar chart to the bottom and remove Dynamic Cost Router**

In `App.tsx`:
1. Pass `avgLatencyMs={kpis.avg_latency_ms}` and `p95LatencyMs={kpis.p95_latency_ms}` to `<Sidebar>`.
2. Move `<AnalyticsChart />` from above `StreamFeed` to below the 2-column grid.
3. Remove the bottom 3 cards (`Top SHAP`, `Dynamic Cost Router`, and `Real-Time Engine SLA`).

- [ ] **Step 2: Verify TypeScript compilation**

Run: `npm --prefix frontend run build`

- [ ] **Step 3: Commit Task 4**

```bash
git add frontend/src/App.tsx
git commit -m "refactor(ui): reorganize dashboard layout with bar chart at bottom and removed cost router card"
```

---

### Task 5: Container Deployment & Visual Verification

**Files:**
- Container: `react-frontend`

- [ ] **Step 1: Rebuild container**

Run: `docker compose up --build -d react-frontend`

- [ ] **Step 2: Verify live UI via Chrome DevTools MCP**

1. Navigate to `http://127.0.0.1:3000/?t=<timestamp>`.
2. Capture screenshot of reorganized Dashboard.
3. Test clicking a transaction row and verify reactive highlight on forensics station.
4. Test clicking `"View All"` button in Stream Forensics.

- [ ] **Step 3: Run backend regression tests**

Run: `$env:PYTHONPATH="."; .\.venv\Scripts\pytest.exe tests/test_stream_api.py -v`

- [ ] **Step 4: Verify 100% clean git status**
