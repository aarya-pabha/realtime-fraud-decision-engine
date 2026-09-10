import React, { useState } from 'react';
import { Plus, RotateCcw, Check } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  onOpenScenarioModal: () => void;
  onReplayStream: () => Promise<void>;
  onInjectDriftWave?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ 
  activeTab,
  onOpenScenarioModal, 
  onReplayStream,
  onInjectDriftWave,
}) => {
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayedFeedback, setReplayedFeedback] = useState(false);

  const handleReplay = async () => {
    setIsReplaying(true);
    try {
      await onReplayStream();
      setReplayedFeedback(true);
      setTimeout(() => setReplayedFeedback(false), 2000);
    } catch (err) {
      console.error('Replay error:', err);
    } finally {
      setIsReplaying(false);
    }
  };

  const getHeaderContent = () => {
    switch (activeTab) {
      case 'simulator':
        return {
          title: '3DS Policy & Decisioning Sandbox',
          subtitle: 'Interactive parameter experimentation across velocity bursts, high-value orders & 3DS routing.',
          actionText: 'Custom Payload',
        };
      case 'drift':
        return {
          title: 'Evidently AI Model Stability & Drift',
          subtitle: 'Distribution monitoring across payments, burst velocities, and 120-day ground-truth label maturity.',
          actionText: 'Inject Drift Payload',
        };
      case 'dashboard':
      default:
        return {
          title: 'Fraud Operations Console',
          subtitle: 'Real-time Bayesian decisioning, online feature hydration & live streaming telemetry.',
          actionText: 'Simulate Transaction',
        };
    }
  };

  const headerMeta = getHeaderContent();

  return (
    <header className="mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2">
        {/* Title */}
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl lg:text-3xl font-extrabold text-[#202318] tracking-tight">
              {headerMeta.title}
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-mono font-bold text-[#006323] shadow-xs">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#006323]" />
              </span>
              <span>8–10 tx/s Ingest</span>
            </span>
          </div>
          <p className="text-xs lg:text-sm text-[#707367] mt-1 font-medium">
            {headerMeta.subtitle}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={activeTab === 'drift' && onInjectDriftWave ? onInjectDriftWave : onOpenScenarioModal}
            className="h-10 px-4 rounded-xl bg-[#006323] text-white text-sm font-bold flex items-center gap-2 shadow-md hover:bg-[#004d1b] hover:scale-102 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{headerMeta.actionText}</span>
          </button>

          <button
            onClick={handleReplay}
            disabled={isReplaying}
            className="h-10 px-4 rounded-xl border border-[#e9ebe3] bg-white hover:bg-[#f1f3ee] text-[#202318] text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-xs disabled:opacity-60"
          >
            {isReplaying ? (
              <>
                <RotateCcw className="w-4 h-4 text-[#006323] animate-spin" />
                <span>Replaying...</span>
              </>
            ) : replayedFeedback ? (
              <>
                <Check className="w-4 h-4 text-[#006323]" />
                <span className="text-[#006323] font-bold">Stream Rewound!</span>
              </>
            ) : (
              <>
                <RotateCcw className="w-4 h-4 text-[#006323]" />
                <span>Replay Stream</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
