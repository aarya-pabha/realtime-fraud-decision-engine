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
