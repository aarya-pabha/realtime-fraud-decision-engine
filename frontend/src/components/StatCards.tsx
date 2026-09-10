import React from 'react';
import { TrendingUp, ShieldCheck, AlertCircle, Scale } from 'lucide-react';
import type { StreamKpis } from '../types';

interface StatCardsProps {
  kpis: StreamKpis;
}

export const StatCards: React.FC<StatCardsProps> = ({ kpis }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Card 1: Holdout Test Streamed (Unified Executive Card with Streaming Ingest Pulse) */}
      <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#006323]" />
            </span>
            <span className="text-xs font-semibold text-[#707367] tracking-wide">
              Holdout Stream Ingest
            </span>
          </div>
          <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <TrendingUp className="w-4 h-4 text-[#006323]" />
          </div>
        </div>
        <p className="text-2xl lg:text-3xl font-extrabold mb-3 tracking-tight mono-num text-[#202318]">
          {kpis.total_processed.toLocaleString()} <span className="text-sm text-[#707367] font-normal">/ {kpis.total_holdout_pool ? kpis.total_holdout_pool.toLocaleString() : '92,427'}</span>
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
          <span className="font-semibold text-[#006323]">IEEE-CIS Month 6</span>
          <span>• Single-Pass LightGBM</span>
        </div>
      </div>

      {/* Card 2: Direct Approvals */}
      <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold text-[#707367] tracking-wide">
            Direct Approvals
          </span>
          <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <ShieldCheck className="w-4 h-4 text-[#006323]" />
          </div>
        </div>
        <p className="text-3xl lg:text-4xl font-extrabold mb-3 tracking-tight mono-num text-[#202318]">
          {kpis.approval_rate_pct.toFixed(1)}%
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
          <span className="font-semibold text-[#006323]">0% Friction</span>
          <span>• $0.00 Authorization Cost</span>
        </div>
      </div>

      {/* Card 3: Dynamic 3DS Challenges */}
      <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-semibold text-[#707367] tracking-wide">
            Dynamic 3DS Challenges
          </span>
          <div className="w-8 h-8 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
            <AlertCircle className="w-4 h-4 text-amber-700" />
          </div>
        </div>
        <p className="text-3xl lg:text-4xl font-extrabold mb-3 tracking-tight mono-num text-[#202318]">
          {kpis.step_up_rate_pct.toFixed(1)}%
        </p>
        <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
          <span className="font-semibold text-amber-700">EMVCo Step-Up</span>
          <span>• $0.05 Verification Fee</span>
        </div>
      </div>

      {/* Card 4: Realized Chargeback Ratio */}
      {(() => {
        const isCompliant = (kpis.chargeback_ratio_pct ?? 0.0) < 1.00;
        return (
          <div className="bg-white border border-[#e9ebe3] text-[#202318] rounded-2xl p-5 shadow-xs transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 group">
            <div className="flex items-start justify-between mb-3">
              <span className="text-xs font-semibold text-[#707367] tracking-wide">
                Portfolio Chargeback Rate
              </span>
              <div className={`w-8 h-8 rounded-xl border flex items-center justify-center transition-transform duration-300 group-hover:scale-110 ${
                isCompliant
                  ? 'bg-emerald-50 border-emerald-100'
                  : 'bg-rose-50 border-rose-100'
              }`}>
                <Scale className={`w-4 h-4 ${isCompliant ? 'text-[#006323]' : 'text-rose-600'}`} />
              </div>
            </div>
            <p className={`text-3xl lg:text-4xl font-extrabold mb-3 tracking-tight mono-num ${
              isCompliant ? 'text-[#006323]' : 'text-rose-700'
            }`}>
              {kpis.chargeback_ratio_pct.toFixed(2)}%
            </p>
            <div className="flex items-center gap-1.5 text-xs text-[#707367] font-medium">
              <span className={`font-semibold ${isCompliant ? 'text-[#006323]' : 'text-rose-700'}`}>
                Visa VAMP / MC ECP
              </span>
              <span>• {isCompliant ? '<1.00% Regulatory Pass' : '≥1.00% Regulatory Breach'}</span>
            </div>
          </div>
        );
      })()}
    </div>

  );
};
