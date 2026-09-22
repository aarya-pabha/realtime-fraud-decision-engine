import React from 'react';
import { 
  LayoutDashboard, 
  SlidersHorizontal, 
  ShieldAlert, 
  ShieldCheck,
  Zap
} from 'lucide-react';

import type { TransactionItem } from '../types';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  streamOnline: boolean;
  avgLatencyMs?: number;
  p95LatencyMs?: number;
  selectedTx?: TransactionItem | null;
}

// Convert screaming snake_case reason codes into human-readable banking terms
const formatReasonCode = (code: string): string => {
  const overrides: Record<string, string> = {
    HIGH_VELOCITY_ASSOCIATED_PHONE_COUNT: 'Phone Burst Velocity',
    RISK_INDICATOR_R_EMAILDOMAIN: 'Recipient Email Risk',
    RISK_INDICATOR_P_EMAILDOMAIN: 'Purchaser Email Risk',
    IRREGULAR_TRANSACTION_CYCLE_DELTA: 'Irregular Timing Cycle',
    UNUSUAL_TRANSACTION_AMOUNT: 'High Purchase Amount',
    UNUSUAL_PAYMENT_COUNT_BURST: 'Rapid Payment Spike',
    HIGH_RISK_CARD_TYPE_CATEGORY: 'Card Category Risk',
    HIGH_CROSS_MERCHANT_CARD_COUNT: 'Cross-Merchant Spike',
    NORMAL_ACCOUNT_BEHAVIOR: 'Clean Baseline',
    LOW_RISK_TRANSACTION_AMOUNT: 'Standard Purchase Amount',
    VERIFIED_DEVICE_BASELINE: 'Device Baseline',
  };
  if (overrides[code]) return overrides[code];

  return code
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const Sidebar: React.FC<SidebarProps> = ({ 
  activeTab, 
  setActiveTab, 
  streamOnline,
  avgLatencyMs = 1.42,
  p95LatencyMs = 15.20,
  selectedTx,
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
                <SlidersHorizontal className="w-4 h-4" />
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
            <span className={`text-[9px] font-bold border px-2 py-0.5 rounded-full ${
              p95LatencyMs <= 25.0
                ? 'bg-emerald-950 text-emerald-300 border-emerald-800/60'
                : 'bg-rose-950 text-rose-300 border-rose-800/60'
            }`}>
              {p95LatencyMs <= 25.0 ? 'p95 < 25ms' : 'p95 > 25ms Spike'}
            </span>
          </div>
          <div className="text-2xl font-black tracking-tight mono-num text-white my-1">
            {avgLatencyMs.toFixed(2)} <span className="text-xs font-normal text-gray-400">ms</span>
          </div>
          <p className="text-[10px] text-gray-400 font-medium">
            p95: {p95LatencyMs.toFixed(2)} ms • Single-pass LightGBM
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
              {selectedTx && selectedTx.reason_codes && selectedTx.reason_codes.length > 0
                ? `Tx #${selectedTx.transaction_id}`
                : selectedTx?.action === 'APPROVE'
                ? 'Fast-Path'
                : 'TreeSHAP'}
            </span>
          </div>

          {selectedTx && selectedTx.reason_codes && selectedTx.reason_codes.length > 0 ? (
            <div className="flex flex-col gap-1.5 text-xs">
              {selectedTx.reason_codes.slice(0, 4).map((rc, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-[#202318] truncate" title={formatReasonCode(rc)}>
                    {formatReasonCode(rc)}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full mono-num border ${
                    selectedTx.action === 'DECLINE'
                      ? 'text-[#b91c1c] bg-[#feecee] border-[#fecaca]'
                      : 'text-[#b45309] bg-[#fef7e6] border-[#fde68a]'
                  }`}>
                    #{idx + 1}
                  </span>
                </div>
              ))}
            </div>
          ) : selectedTx?.action === 'APPROVE' ? (
            <div className="py-1">
              <div className="flex items-center gap-1.5 text-[#006323] font-bold text-xs mb-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Clean Baseline Flow</span>
              </div>
              <p className="text-[10px] text-[#707367] leading-snug">
                TreeSHAP bypassed on fast-path approval. Zero adverse signals.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-[#202318] truncate">Transaction Amount</span>
                <span className="text-[10px] font-bold text-[#006323] bg-[#e6f7ec] border border-[#a7f3d0] px-1.5 py-0.2 rounded-full mono-num">#1</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-[#202318] truncate">5m Card Velocity</span>
                <span className="text-[10px] font-bold text-[#006323] bg-[#e6f7ec] border border-[#a7f3d0] px-1.5 py-0.2 rounded-full mono-num">#2</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-[#202318] truncate">Disposable Email</span>
                <span className="text-[10px] font-bold text-[#006323] bg-[#e6f7ec] border border-[#a7f3d0] px-1.5 py-0.2 rounded-full mono-num">#3</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-[#202318] truncate">Account Tenancy</span>
                <span className="text-[10px] font-bold text-[#006323] bg-[#e6f7ec] border border-[#a7f3d0] px-1.5 py-0.2 rounded-full mono-num">#4</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
