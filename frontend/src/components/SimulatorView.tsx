import React from 'react';
import { ShieldCheck, AlertTriangle, ShieldX, Clock, DollarSign, Activity } from 'lucide-react';
import { StatusPill } from './StatusPill';
import type { TransactionItem } from '../types';

interface SimulatorViewProps {
  selectedTx: TransactionItem | null;
  onSimulatePreset: (preset: 'attack' | 'highval' | 'normal') => void;
  onCustomSimulate?: (payload: Record<string, unknown>) => void;
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
                  selectedTx.reason_codes.map((rc: string, idx: number) => (
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
                  <StatusPill variant="success" size="sm" icon={<ShieldCheck className="w-3.5 h-3.5" />}>
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
