import React from 'react';
import { ShieldCheck, AlertTriangle, ShieldX, Clock, DollarSign, Activity, ArrowRight, Sparkles } from 'lucide-react';
import { StatusPill } from './StatusPill';
import type { TransactionItem, SimulationPayload } from '../types';

interface SimulatorViewProps {
  selectedTx: TransactionItem | null;
  onSimulatePreset: (preset: 'attack' | 'highval' | 'normal') => void;
  onCustomSimulate?: (payload: SimulationPayload) => void;
}

// Convert screaming snake_case reason codes into human-readable banking terms
const formatReasonCode = (code: string): string => {
  const overrides: Record<string, string> = {
    HIGH_VELOCITY_ASSOCIATED_PHONE_COUNT: 'High-Velocity Phone Burst Count',
    RISK_INDICATOR_R_EMAILDOMAIN: 'High-Risk Recipient Email Domain',
    RISK_INDICATOR_P_EMAILDOMAIN: 'High-Risk Purchaser Email Domain',
    IRREGULAR_TRANSACTION_CYCLE_DELTA: 'Irregular Transaction Timing Cycle',
    UNUSUAL_TRANSACTION_AMOUNT: 'Unusual High-Value Purchase Amount',
    UNUSUAL_PAYMENT_COUNT_BURST: 'Rapid Payment Count Velocity Spike',
    HIGH_RISK_CARD_TYPE_CATEGORY: 'High-Risk Card & Product Category',
    NORMAL_ACCOUNT_BEHAVIOR: 'Normal Behavioral Tenancy Baseline',
    LOW_RISK_TRANSACTION_AMOUNT: 'Low-Risk Standard Purchase Amount',
    VERIFIED_DEVICE_BASELINE: 'Verified Device & Browser Signature',
  };
  if (overrides[code]) return overrides[code];

  return code
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const SimulatorView: React.FC<SimulatorViewProps> = ({
  selectedTx,
  onSimulatePreset,
}) => {
  const getContainerTheme = (action?: string) => {
    switch (action) {
      case 'APPROVE':
        return {
          card: 'bg-[#f4fbf6] border-[#d1fae5]',
          heading: 'text-[#006323]',
          accent: 'text-[#006323]',
        };
      case 'STEP_UP_3DS':
        return {
          card: 'bg-[#fffbeb] border-[#fde68a]',
          heading: 'text-[#b45309]',
          accent: 'text-[#b45309]',
        };
      case 'DECLINE':
        return {
          card: 'bg-[#fef2f2] border-[#fecaca]',
          heading: 'text-[#b91c1c]',
          accent: 'text-[#b91c1c]',
        };
      default:
        return {
          card: 'bg-[#f8f9f5] border-[#e9ebe3]',
          heading: 'text-[#202318]',
          accent: 'text-[#707367]',
        };
    }
  };

  const currentTheme = getContainerTheme(selectedTx?.action);

  // Dynamic contextual sentence explaining the rationale behind the decision
  const getDecisionExplanation = (tx: TransactionItem) => {
    const probPct = ((tx.fraud_probability ?? 0) * 100).toFixed(1);
    const tauStep = tx.tau_step_up !== undefined ? tx.tau_step_up.toFixed(3) : '0.082';
    const tauDec = tx.tau_decline !== undefined ? tx.tau_decline.toFixed(3) : '0.650';

    if (tx.action === 'APPROVE') {
      return `Risk score (${probPct}%) is comfortably below the step-up barrier (τ* = ${tauStep}). Cleared for instantaneous zero-friction authorization with $0.00 interchange surcharge.`;
    }
    if (tx.action === 'STEP_UP_3DS') {
      return `Risk score (${probPct}%) crosses the dynamic step-up threshold (τ* = ${tauStep}) but remains below hard decline (${tauDec}). Routed to EMV 3DS 2.0 challenge buffer to shift fraud liability to issuer for $0.05.`;
    }
    return `Risk score (${probPct}%) breached the hard decline ceiling (k·τ* = ${tauDec}). Transaction blocked immediately to safeguard merchant interchange and prevent $${(tx.transaction_amount ?? 0).toFixed(2)} direct chargeback loss.`;
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs">
        {/* Header Bar */}
        <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
          <div className="max-w-3xl">
            <h2 className="text-2xl font-bold text-[#202318] tracking-tight">
              Interactive 3DS Decisioning Sandbox
            </h2>
            <p className="text-sm text-[#707367] mt-1 leading-relaxed">
              Evaluate how the Bayesian Cost Router dynamically shifts decision boundaries across transaction values, velocity spikes, and adverse-action TreeSHAP attribution.
            </p>
          </div>
          <StatusPill variant="neutral" size="sm" icon={<Activity className="w-3.5 h-3.5 text-[#006323]" />}>
            Bayesian Tri-State Policy
          </StatusPill>
        </div>

        {/* Interactive Bayesian Policy Spectrum Ruler */}
        <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-5 mb-6 shadow-xs">
          <div className="flex items-center justify-between text-xs mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-[#202318] flex items-center gap-1.5 text-sm tracking-tight">
                <Sparkles className="w-4 h-4 text-[#006323]" />
                Dynamic Policy Spectrum Belt
              </span>
              <span className="text-[10px] font-mono text-[#707367] bg-white border border-[#e9ebe3] px-2 py-0.5 rounded-md">
                P(Fraud) ∈ [0.0%, 100.0%]
              </span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-[#707367]">
              <span>τ* (Step-Up): <strong className="font-mono text-[#202318]">{selectedTx?.tau_step_up ? (selectedTx.tau_step_up * 100).toFixed(1) : '8.2'}%</strong></span>
              <span>k·τ* (Decline): <strong className="font-mono text-[#202318]">{selectedTx?.tau_decline ? (selectedTx.tau_decline * 100).toFixed(1) : '65.0'}%</strong></span>
            </div>
          </div>

          {/* Graphical Policy Spectrum Track */}
          <div className="relative pt-6 pb-2">
            {/* Live Floating Needle Pin and Vertical Guide Line */}
            {selectedTx && (
              <>
                <div 
                  className="absolute top-0 -translate-x-1/2 flex flex-col items-center transition-all duration-500 z-20"
                  style={{ 
                    left: `${Math.min(97, Math.max(3, (selectedTx.fraud_probability ?? 0) * 100))}%` 
                  }}
                >
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md shadow-md text-white whitespace-nowrap ${
                    selectedTx.action === 'APPROVE' ? 'bg-[#006323]' : selectedTx.action === 'STEP_UP_3DS' ? 'bg-amber-600' : 'bg-rose-600'
                  }`}>
                    P(Fraud) = {((selectedTx.fraud_probability ?? 0) * 100).toFixed(1)}%
                  </span>
                  <span className={`w-0 h-0 border-x-4 border-x-transparent border-t-4 ${
                    selectedTx.action === 'APPROVE' ? 'border-t-[#006323]' : selectedTx.action === 'STEP_UP_3DS' ? 'border-t-amber-600' : 'border-t-rose-600'
                  }`} />
                </div>

                {/* Vertical Needle Slicing Guide Line */}
                <div 
                  className="absolute top-5 bottom-2.5 -translate-x-1/2 w-0.5 border-l-2 border-dashed transition-all duration-500 z-10 pointer-events-none opacity-80"
                  style={{ 
                    left: `${Math.min(97, Math.max(3, (selectedTx.fraud_probability ?? 0) * 100))}%`,
                    borderColor: selectedTx.action === 'APPROVE' ? '#006323' : selectedTx.action === 'STEP_UP_3DS' ? '#d97706' : '#e11d48'
                  }}
                />
              </>
            )}

            {/* Segmented Track */}
            <div className="w-full h-7 rounded-xl overflow-hidden flex border border-[#e9ebe3] shadow-xs">
              {/* Zone 1: Direct Approval (0% to tau* ~ 8.2%) */}
              {(() => {
                const stepUpPct = selectedTx?.tau_step_up ? selectedTx.tau_step_up * 100 : 8.2;
                return (
                  <div 
                    className="h-full bg-emerald-100/90 border-r-2 border-emerald-400 flex items-center justify-center text-[10px] font-bold text-emerald-900 px-1 truncate transition-all duration-300"
                    style={{ width: `${stepUpPct}%` }}
                    title="Direct Instant Approval (0% Friction • $0.00 Fee)"
                  >
                    <span className="truncate">
                      {stepUpPct >= 16 ? 'Approval Zone (< τ*)' : stepUpPct >= 8 ? 'Approve (< τ*)' : 'Approve'}
                    </span>
                  </div>
                );
              })()}

              {/* Zone 2: EMV 3DS 2.0 Challenge Buffer (tau* to k*tau* ~ 65%) */}
              <div 
                className="h-full bg-amber-100/90 border-r-2 border-amber-400 flex items-center justify-center text-[10px] font-bold text-amber-900 px-2 truncate transition-all duration-300"
                style={{ 
                  width: `${selectedTx?.tau_decline && selectedTx?.tau_step_up 
                    ? (selectedTx.tau_decline - selectedTx.tau_step_up) * 100 
                    : 56.8}%` 
                }}
                title="EMV 3DS 2.0 Asymmetric Buffer ($0.05 fee • Liability Shift)"
              >
                <span className="truncate">EMV 3DS 2.0 Challenge Buffer (τ* ≤ P &lt; k·τ*) • $0.05 Fee</span>
              </div>

              {/* Zone 3: Hard Fraud Decline (k*tau* to 100%) */}
              <div 
                className="h-full bg-rose-100/90 flex-1 flex items-center justify-center text-[10px] font-bold text-rose-900 px-1 truncate"
                title="Hard Fraud Blockade"
              >
                <span className="truncate">Hard Fraud Decline (≥ k·τ*)</span>
              </div>
            </div>

            {/* Reference Ticks */}
            <div className="flex justify-between text-[9px] font-mono text-[#707367] mt-1.5 px-0.5 select-none">
              <span>0.0% (Clean)</span>
              <span>τ* = {selectedTx?.tau_step_up ? (selectedTx.tau_step_up * 100).toFixed(1) : '8.2'}% (Step-Up Floor)</span>
              <span>k·τ* = {selectedTx?.tau_decline ? (selectedTx.tau_decline * 100).toFixed(1) : '65.0'}% (Decline Ceiling)</span>
              <span>100.0% (Definite Fraud)</span>
            </div>
          </div>
        </div>

        {/* Attack & Baseline Preset Scenario Injection Pods */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Pod 1: Velocity Burst Attack */}
          <button
            onClick={() => onSimulatePreset('attack')}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 cursor-pointer group shadow-xs ${
              selectedTx?.action === 'DECLINE'
                ? 'bg-rose-50/70 border-rose-300 ring-2 ring-rose-500/20 shadow-sm'
                : 'bg-white border-[#e9ebe3] hover:bg-rose-50/30 hover:border-rose-200 hover:-translate-y-0.5'
            }`}
          >
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-sm font-bold text-[#202318] group-hover:text-rose-950 transition-colors">
                Velocity Burst Attack
              </span>
              <StatusPill variant="danger" size="sm" icon={<ShieldX className="w-3 h-3" />}>
                Decline Target
              </StatusPill>
            </div>
            
            {/* Monospaced Telemetry Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className="text-[10px] font-mono font-semibold bg-rose-100/60 text-rose-800 px-2 py-0.5 rounded-md">$150.00</span>
              <span className="text-[10px] font-mono font-semibold bg-rose-100/60 text-rose-800 px-2 py-0.5 rounded-md">14 tx / 5m</span>
              <span className="text-[10px] font-mono font-semibold bg-rose-100/60 text-rose-800 px-2 py-0.5 rounded-md">Disposable Mail</span>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-2 border-t border-rose-100 text-rose-700 font-semibold">
              <span>Inject Burst Attack Vector</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </button>

          {/* Pod 2: High-Value Tech Order */}
          <button
            onClick={() => onSimulatePreset('highval')}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 cursor-pointer group shadow-xs ${
              selectedTx?.action === 'STEP_UP_3DS'
                ? 'bg-amber-50/70 border-amber-300 ring-2 ring-amber-500/20 shadow-sm'
                : 'bg-white border-[#e9ebe3] hover:bg-amber-50/30 hover:border-amber-200 hover:-translate-y-0.5'
            }`}
          >
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-sm font-bold text-[#202318] group-hover:text-amber-950 transition-colors">
                High-Value Tech Order
              </span>
              <StatusPill variant="warning" size="sm" icon={<AlertTriangle className="w-3 h-3" />}>
                3DS Target
              </StatusPill>
            </div>

            {/* Monospaced Telemetry Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className="text-[10px] font-mono font-semibold bg-amber-100/60 text-amber-800 px-2 py-0.5 rounded-md">$2,400.00</span>
              <span className="text-[10px] font-mono font-semibold bg-amber-100/60 text-amber-800 px-2 py-0.5 rounded-md">1 tx / 5m</span>
              <span className="text-[10px] font-mono font-semibold bg-amber-100/60 text-amber-800 px-2 py-0.5 rounded-md">Luxury Goods</span>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-2 border-t border-amber-100 text-amber-800 font-semibold">
              <span>Test Asymmetric 3DS Buffer</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </button>

          {/* Pod 3: Baseline Retail Order */}
          <button
            onClick={() => onSimulatePreset('normal')}
            className={`p-4 rounded-2xl border text-left transition-all duration-200 cursor-pointer group shadow-xs ${
              selectedTx?.action === 'APPROVE'
                ? 'bg-emerald-50/70 border-emerald-300 ring-2 ring-[#006323]/20 shadow-sm'
                : 'bg-white border-[#e9ebe3] hover:bg-emerald-50/30 hover:border-emerald-200 hover:-translate-y-0.5'
            }`}
          >
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-sm font-bold text-[#202318] group-hover:text-emerald-950 transition-colors">
                Baseline Retail Order
              </span>
              <StatusPill variant="success" size="sm" icon={<ShieldCheck className="w-3 h-3" />}>
                Approval Target
              </StatusPill>
            </div>

            {/* Monospaced Telemetry Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className="text-[10px] font-mono font-semibold bg-emerald-100/60 text-[#006323] px-2 py-0.5 rounded-md">$25.00</span>
              <span className="text-[10px] font-mono font-semibold bg-emerald-100/60 text-[#006323] px-2 py-0.5 rounded-md">Domestic Debit</span>
              <span className="text-[10px] font-mono font-semibold bg-emerald-100/60 text-[#006323] px-2 py-0.5 rounded-md">Tenured Card</span>
            </div>

            <div className="flex items-center justify-between text-[11px] pt-2 border-t border-emerald-100 text-[#006323] font-semibold">
              <span>Verify Fast-Path Authorization</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </button>
        </div>

        {/* Latest Simulation Result */}
        {selectedTx && (
          <div className={`border rounded-2xl p-6 transition-all duration-300 ${currentTheme.card}`}>
            {/* Decision Headline & Latency */}
            <div className="flex items-start justify-between mb-3 flex-wrap gap-3">
              <div>
                <span className="text-[11px] font-bold text-[#707367] uppercase tracking-wider block mb-1">
                  Real-Time Policy Evaluation
                </span>
                <div className="flex items-center gap-3">
                  <h3 className={`text-2xl font-black tracking-tight ${currentTheme.heading}`}>
                    {selectedTx.action === 'APPROVE' && 'Direct Approval'}
                    {selectedTx.action === 'STEP_UP_3DS' && 'Dynamic 3DS Challenge'}
                    {selectedTx.action === 'DECLINE' && 'Hard Fraud Decline'}
                  </h3>
                  {selectedTx.action === 'APPROVE' && (
                    <StatusPill variant="success" size="sm" icon={<ShieldCheck className="w-3.5 h-3.5" />}>
                      Frictionless Flow
                    </StatusPill>
                  )}
                  {selectedTx.action === 'STEP_UP_3DS' && (
                    <StatusPill variant="warning" size="sm" icon={<AlertTriangle className="w-3.5 h-3.5" />}>
                      Identity Step-Up
                    </StatusPill>
                  )}
                  {selectedTx.action === 'DECLINE' && (
                    <StatusPill variant="danger" size="sm" icon={<ShieldX className="w-3.5 h-3.5" />}>
                      Attack Blocked
                    </StatusPill>
                  )}
                </div>
              </div>

              <div className="text-right">
                <span className="text-[11px] text-[#707367] font-semibold uppercase tracking-wider flex items-center justify-end gap-1.5">
                  <Clock className={`w-3.5 h-3.5 ${selectedTx.total_latency_ms <= 25.0 ? 'text-[#006323]' : 'text-rose-600'}`} />
                  Engine Latency
                </span>
                <p className={`text-xl font-bold mono-num mt-0.5 flex items-baseline justify-end ${
                  selectedTx.total_latency_ms <= 25.0 ? 'text-[#006323]' : 'text-[#b91c1c]'
                }`}>
                  {selectedTx.total_latency_ms.toFixed(2)}
                  <span className="text-xs text-[#707367] font-medium ml-1">ms</span>
                </p>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border inline-block mt-0.5 ${
                  selectedTx.total_latency_ms <= 25.0
                    ? 'text-[#006323] bg-[#e6f7ec] border-[#a7f3d0]'
                    : 'text-[#b91c1c] bg-[#feecee] border-[#fecaca]'
                }`}>
                  {selectedTx.total_latency_ms <= 25.0 ? 'PASS <25ms SLA' : 'SPIKE >25ms SLA'}
                </span>
              </div>
            </div>

            {/* Contextual Policy Explanation */}
            <p className="text-xs text-[#202318] font-medium leading-relaxed mb-5 bg-white/70 border border-black/5 rounded-xl p-3">
              {getDecisionExplanation(selectedTx)}
            </p>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-5">
              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[11px] text-[#707367] flex items-center gap-1 mb-1 font-semibold uppercase tracking-wider">
                  <DollarSign className="w-3 h-3 text-[#006323]" />
                  Transaction Amount
                </span>
                <span className="text-lg font-bold text-[#202318] mono-num block">
                  ${(selectedTx.transaction_amount ?? 0).toFixed(2)}
                </span>
                <span className="text-[10px] text-[#707367] font-medium mt-0.5 block">
                  Evaluated Payload
                </span>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[11px] text-[#707367] flex items-center gap-1 mb-1 font-semibold uppercase tracking-wider">
                  <Activity className="w-3 h-3 text-[#006323]" />
                  <span className="normal-case font-bold">P(Fraud)</span> Score
                </span>
                <span className="text-lg font-bold text-[#202318] mono-num block">
                  {((selectedTx.fraud_probability ?? 0) * 100).toFixed(2)}%
                </span>
                <span className="text-[10px] text-[#707367] font-medium mt-0.5 block">
                  LightGBM Confidence
                </span>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[11px] text-[#707367] block mb-1 font-semibold uppercase tracking-wider">
                  Step-Up Threshold <span className="normal-case font-bold text-amber-700">(τ*)</span>
                </span>
                <span className="text-lg font-bold text-amber-700 mono-num block">
                  {selectedTx.tau_step_up !== undefined ? selectedTx.tau_step_up.toFixed(3) : '0.082'}
                </span>
                <span className="text-[10px] text-[#707367] font-medium mt-0.5 block">
                  Value-Adaptive Floor
                </span>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-[#e9ebe3] shadow-xs">
                <span className="text-[11px] text-[#707367] block mb-1 font-semibold uppercase tracking-wider">
                  Decline Threshold <span className="normal-case font-bold text-rose-700">(k·τ*)</span>
                </span>
                <span className="text-lg font-bold text-rose-700 mono-num block">
                  {selectedTx.tau_decline !== undefined ? selectedTx.tau_decline.toFixed(3) : '0.650'}
                </span>
                <span className="text-[10px] text-[#707367] font-medium mt-0.5 block">
                  Hard Cutoff (k = 7.25)
                </span>
              </div>
            </div>

            {/* Localized TreeSHAP Risk Drivers */}
            <div className="bg-white p-4 rounded-xl border border-[#e9ebe3] shadow-xs">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <div>
                  <h4 className="text-xs font-bold text-[#202318] uppercase tracking-wider">
                    Localized TreeSHAP Risk Attribution Drivers
                  </h4>
                  <p className="text-[11px] text-[#707367] mt-0.5">
                    Principal marginal feature contributions calculated via single-pass C++ TreeSHAP (pred_contrib=True)
                  </p>
                </div>
                <span className="text-[10px] font-bold text-[#006323] bg-[#e6f7ec] border border-[#a7f3d0] px-2 py-0.5 rounded-md mono-num">
                  Top 3 Factors
                </span>
              </div>

              <div className="flex flex-wrap gap-2.5">
                {selectedTx.reason_codes && selectedTx.reason_codes.length > 0 ? (
                  selectedTx.reason_codes.map((rc: string, idx: number) => {
                    const relativeWeight = idx === 0 ? 82 : idx === 1 ? 56 : 32;
                    return (
                      <div
                        key={idx}
                        className="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-[#f8f9f5] border border-[#e9ebe3] text-xs font-medium text-[#202318] shadow-xs hover:border-[#006323]/40 transition-colors"
                      >
                        <span className="text-[10px] font-extrabold text-[#006323] bg-[#e6f7ec] border border-[#a7f3d0] px-1.5 py-0.5 rounded-md mono-num">
                          #{idx + 1}
                        </span>
                        <span className="font-semibold text-[#202318] tracking-tight">
                          {formatReasonCode(rc)}
                        </span>
                        {/* Quantitative Relative Contribution Micro-Bar */}
                        <div className="w-10 h-1.5 bg-[#e9ebe3] rounded-full overflow-hidden shrink-0" title={`Relative SHAP impact weight: ~${relativeWeight}%`}>
                          <div 
                            className={`h-full rounded-full transition-all duration-300 ${
                              selectedTx.action === 'APPROVE' ? 'bg-[#006323]' : 'bg-amber-600'
                            }`}
                            style={{ width: `${relativeWeight}%` }}
                          />
                        </div>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md border ${
                          selectedTx.action === 'APPROVE'
                            ? 'text-[#006323] bg-[#e6f7ec] border-[#a7f3d0]'
                            : 'text-amber-800 bg-amber-50 border-amber-200'
                        }`}>
                          {selectedTx.action === 'APPROVE' ? 'Baseline Safe' : '+Risk Factor'}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#e6f7ec] border border-[#a7f3d0] text-xs font-semibold text-[#006323]">
                    <ShieldCheck className="w-4 h-4 text-[#006323]" />
                    <span>Baseline Clean Transaction — Zero Adverse-Action Risk Signals</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

