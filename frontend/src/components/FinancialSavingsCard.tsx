import React from 'react';
import { ShieldCheck, TrendingUp, DollarSign, CheckCircle2, Scale } from 'lucide-react';
import type { StreamKpis } from '../types';

interface FinancialSavingsCardProps {
  kpis: StreamKpis;
}

export const FinancialSavingsCard: React.FC<FinancialSavingsCardProps> = ({ kpis }) => {
  // Pure live streaming financial KPIs
  const liveNetSavings = kpis.net_savings_dollars ?? 0.0;
  const livePrevented = kpis.prevented_fraud_dollars ?? 0.0;
  const liveFrictionSaved = kpis.friction_saved_dollars ?? 0.0;
  const liveLiabilityShifted = kpis.liability_shifted_dollars ?? 0.0;
  const liveStaticLoss = kpis.static_loss_dollars ?? 0.0;
  const liveTunedStaticLoss = kpis.tuned_static_loss_dollars ?? 0.0;
  const liveDynamicLoss = kpis.dynamic_loss_dollars ?? 0.0;

  // Dynamic comparative loss percentages
  const lossPercentage = liveStaticLoss > 0
    ? Math.max(0, Math.min(100, (liveDynamicLoss / liveStaticLoss) * 100))
    : 0.0;
  const savedPercentage = liveStaticLoss > 0 ? 100 - lossPercentage : 100.0;

  // Tuned static 0.17 cutoff comparative percentage
  const tunedLossPercentage = liveStaticLoss > 0
    ? Math.max(0, Math.min(100, (liveTunedStaticLoss / liveStaticLoss) * 100))
    : 0.0;
  const tunedSavedPercentage = liveStaticLoss > 0 ? 100 - tunedLossPercentage : 100.0;

  return (
    <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-lg font-bold text-[#202318] tracking-tight flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-[#006323]" />
              Financial ROI & Capital Loss Prevented
            </h2>
            <span className="text-[11px] font-semibold text-[#006323] bg-[#e6f7ec] px-2.5 py-0.5 rounded-full border border-[#a7f3d0]">
              Dynamic Cost Router
            </span>
          </div>
          <p className="text-xs text-[#707367]">
            Empirical financial performance of live stream value-adaptive Bayesian thresholding vs static 0.50 cutoff.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[#006323] bg-[#f4fbf6] px-3 py-1.5 rounded-xl border border-[#d1fae5] flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{savedPercentage.toFixed(1)}% Net Loss Reduction</span>
          </span>
        </div>
      </div>

      {/* Top 4 Financial Metric Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Metric 1: Total Net Cash Saved */}
        <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4 shadow-xs hover:border-[#006323]/30 transition-all">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-[#707367] uppercase tracking-wider">
              Total Net Cash Saved
            </span>
            <span className="text-[10px] font-bold text-[#006323] bg-[#e6f7ec] px-1.5 py-0.5 rounded-md border border-[#a7f3d0]">
              Live Session ROI
            </span>
          </div>
          <p className="text-2xl font-extrabold text-[#006323] mono-num">
            +${liveNetSavings.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-[#707367] mt-1">
            Prevented fraud + friction saved - 3DS fees
          </p>
        </div>

        {/* Metric 2: Direct Fraud Blocked */}
        <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4 shadow-xs hover:border-[#006323]/30 transition-all">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-[#707367] uppercase tracking-wider">
              Direct Fraud Blocked
            </span>
            <ShieldCheck className="w-4 h-4 text-[#006323]" />
          </div>
          <p className="text-2xl font-extrabold text-[#202318] mono-num">
            ${livePrevented.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-[#707367] mt-1">
            {kpis.declined_count ?? 0} attacks blocked by hard decline
          </p>
        </div>

        {/* Metric 3: Friction Slashed */}
        <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4 shadow-xs hover:border-[#006323]/30 transition-all">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-[#707367] uppercase tracking-wider">
              Friction Slashed
            </span>
            <TrendingUp className="w-4 h-4 text-[#006323]" />
          </div>
          <p className="text-2xl font-extrabold text-[#202318] mono-num">
            +${liveFrictionSaved.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-[#707367] mt-1">
            {kpis.step_up_count ?? 0} false declines avoided via 3DS 2.0 buffer
          </p>
        </div>

        {/* Metric 4: 3DS Liability Shifted */}
        <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4 shadow-xs hover:border-[#006323]/30 transition-all">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-[#707367] uppercase tracking-wider">
              3DS Liability Shifted
            </span>
            <Scale className="w-4 h-4 text-[#006323]" />
          </div>
          <p className="text-2xl font-extrabold text-[#006323] mono-num">
            ${liveLiabilityShifted.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-[#707367] mt-1">
            Fraud chargeback liability shifted to issuer ($0.05/tx fee)
          </p>
        </div>
      </div>

      {/* Comparative Policy Visual Bar */}
      <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-5 shadow-xs">
        <div className="flex items-center justify-between text-xs font-bold text-[#202318] mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-extrabold tracking-tight">Counterfactual Policy Loss Exposure</span>
            <span className="text-[10px] font-mono text-[#707367] bg-white border border-[#e9ebe3] px-2 py-0.5 rounded-md">Live Stream Normalized</span>
          </div>
          <span className="text-xs font-bold text-[#006323] bg-emerald-50 border border-emerald-200/70 px-2.5 py-1 rounded-full mono-num flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#006323]" />
            +${liveNetSavings.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Net Capital Retained
          </span>
        </div>

        {/* Scale Ruler Reference Ticks */}
        <div className="flex justify-between text-[9px] font-mono text-[#707367] px-1 mb-2 select-none">
          <span>0%</span>
          <span>25% EXPOSURE</span>
          <span>50%</span>
          <span>75%</span>
          <span>100% MAXIMUM</span>
        </div>

        {/* 3-Tier Horizontal Stacked Bars */}
        <div className="space-y-4">
          {/* Bar 1: Static 0.50 Policy (Sleek Slate-Carbon Baseline) */}
          <div>
            <div className="flex items-center justify-between text-[11px] text-[#707367] mb-1.5">
              <span className="font-semibold text-slate-700">1. Static 0.50 Cutoff Policy Loss (Naive ML Baseline)</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.2 rounded-md">Reference Baseline</span>
                <span className="font-mono font-bold text-slate-900">${liveStaticLoss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            </div>
            <div className="w-full h-3.5 rounded-full bg-slate-100 border border-slate-200/60 overflow-hidden">
              <div className="w-full h-full bg-slate-600 rounded-full" />
            </div>
          </div>

          {/* Bar 2: Tuned Static Cutoff (tau = 0.17) (Refined Warm Bronze) */}
          <div>
            <div className="flex items-center justify-between text-[11px] text-[#707367] mb-1.5">
              <span className="font-semibold text-amber-900">2. Tuned Static Cutoff (τ = 0.17, Cost-Tuned, No 3DS)</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.2 rounded-md">-{tunedSavedPercentage.toFixed(1)}% Fraud Loss</span>
                <span className="font-mono font-bold text-amber-950">${liveTunedStaticLoss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            </div>
            <div className="w-full h-3.5 rounded-full bg-amber-50/80 border border-amber-200/60 overflow-hidden flex" title="Tuned Static Policy (τ = 0.17): Minimizes expected loss under single-thresholding, but triples customer false decline friction">
              <div className="h-full bg-amber-600 rounded-l-full transition-all duration-500" style={{ width: `${tunedLossPercentage.toFixed(1)}%` }} />
            </div>
          </div>

          {/* Bar 3: Dynamic Cost Router Policy (Precision Emerald & Luminous Mint) */}
          <div>
            <div className="flex items-center justify-between text-[11px] text-[#707367] mb-1.5">
              <span className="font-extrabold text-[#006323]">3. Dynamic Cost Router Realized Loss (Value-Adaptive + 3DS 2.0)</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold text-[#006323] bg-emerald-50 border border-emerald-200 px-2 py-0.2 rounded-md">-{savedPercentage.toFixed(1)}% Net Loss Reduction</span>
                <span className="font-mono font-bold text-[#006323]">${liveDynamicLoss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            </div>
            <div className="w-full h-3.5 rounded-full bg-[#ecfdf5] border border-emerald-200/80 overflow-hidden flex">
              <div className="h-full bg-[#006323] transition-all duration-500" style={{ width: `${lossPercentage.toFixed(1)}%` }} />
              <div className="h-full bg-[#6ee7b7] transition-all duration-500" style={{ width: `${savedPercentage.toFixed(1)}%` }} title="Capital Retained (Net Savings)" />
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center justify-between text-[11px] text-[#707367] mt-4 pt-3 border-t border-[#e9ebe3] flex-wrap gap-2">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-slate-600" />
            <span className="font-medium text-slate-700">Static 0.50 Baseline (Uncalibrated)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-amber-600" />
            <span className="font-medium text-amber-900">Tuned Static (τ = 0.17 Bayes Cutoff)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-[#006323]" />
            <span className="font-medium text-[#006323]">Dynamic Router Realized Loss</span>
          </span>
          <span className="flex items-center gap-1.5 text-[#006323] font-bold">
            <span className="w-2.5 h-2.5 rounded-xs bg-[#6ee7b7]" />
            <span>Capital Retained (Saved Margin)</span>
          </span>
        </div>
      </div>
    </div>
  );
};
