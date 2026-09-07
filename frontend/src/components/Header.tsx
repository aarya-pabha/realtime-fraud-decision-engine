import React, { useState } from 'react';
import { Plus, RotateCcw, Check } from 'lucide-react';

interface HeaderProps {
  onOpenScenarioModal: () => void;
  onReplayStream: () => Promise<void>;
}

export const Header: React.FC<HeaderProps> = ({ 
  onOpenScenarioModal, 
  onReplayStream,
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

  return (
    <header className="mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2">
        {/* Title */}
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-[#202318] tracking-tight">
            Fraud Operations Console
          </h1>
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
