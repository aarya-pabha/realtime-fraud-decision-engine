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
