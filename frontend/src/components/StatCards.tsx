import React from 'react';
import { ArrowUpRight, TrendingUp, ShieldCheck, AlertCircle, DollarSign } from 'lucide-react';
import type { StreamKpis } from '../types';

interface StatCardsProps {
  kpis: StreamKpis;
}

export const StatCards: React.FC<StatCardsProps> = ({ kpis }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Featured Hero Card (Donezo Forest Green) */}
      <div className="bg-[#006323] text-white rounded-2xl p-5 shadow-lg relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold text-white/85 tracking-wide">
            Holdout Test Streamed
          </span>
          <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <ArrowUpRight className="w-3.5 h-3.5 text-white" />
          </div>
        </div>
        <p className="text-2xl lg:text-3xl font-extrabold mb-3 tracking-tight mono-num">
          {kpis.total_processed.toLocaleString()} <span className="text-base text-white/70 font-normal">/ {kpis.total_holdout_pool ? kpis.total_holdout_pool.toLocaleString() : '92,427'}</span>
        </p>
        <div className="flex items-center gap-1.5 text-xs text-white/80 font-medium">
          <TrendingUp className="w-3.5 h-3.5 text-emerald-300" />
          <span>Real Holdout Dataset (Month 6) • Live Model</span>
        </div>
      </div>

      {/* Card 2: Approved Rate */}
      <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold text-[#707367] tracking-wide">
            Direct Approvals
          </span>
          <div className="w-7 h-7 rounded-full bg-[#006323] flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <ArrowUpRight className="w-3.5 h-3.5 text-white" />
          </div>
        </div>
        <p className="text-3xl lg:text-4xl font-extrabold mb-3 tracking-tight mono-num text-[#202318]">
          {kpis.approval_rate_pct.toFixed(1)}%
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
          <ShieldCheck className="w-3.5 h-3.5 text-[#006323]" />
          <span>0% Friction • $0.00 Authorization Cost</span>
        </div>
      </div>

      {/* Card 3: 3DS Step-Up Rate */}
      <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold text-[#707367] tracking-wide">
            Dynamic 3DS Challenges
          </span>
          <div className="w-7 h-7 rounded-full bg-[#006323] flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <ArrowUpRight className="w-3.5 h-3.5 text-white" />
          </div>
        </div>
        <p className="text-3xl lg:text-4xl font-extrabold mb-3 tracking-tight mono-num text-[#202318]">
          {kpis.step_up_rate_pct.toFixed(1)}%
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
          <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
          <span>Step-Up Auth • Avg Cost $0.05 / tx</span>
        </div>
      </div>

      {/* Card 4: Chargeback Ratio */}
      <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold text-[#707367] tracking-wide">
            Chargeback Ratio
          </span>
          <div className="w-7 h-7 rounded-full bg-[#006323] flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <ArrowUpRight className="w-3.5 h-3.5 text-white" />
          </div>
        </div>
        <p className="text-3xl lg:text-4xl font-extrabold mb-3 tracking-tight mono-num text-[#006323]">
          {kpis.chargeback_ratio_pct.toFixed(2)}%
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
          <DollarSign className="w-3.5 h-3.5 text-[#006323]" />
          <span>Visa VAMP Compliant (&lt;1.50% limit)</span>
        </div>
      </div>
    </div>
  );
};
