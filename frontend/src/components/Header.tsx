import React from 'react';
import { Search, Mail, Bell, Plus, PlayCircle } from 'lucide-react';

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
      {/* Top Utility Bar */}
      <div className="flex items-center justify-between gap-4 mb-5">
        {/* Search Pill */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-[#707367] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search transaction, card token, IP..."
            className="w-full h-10 pl-10 pr-12 rounded-full border border-[#e9ebe3] bg-white text-sm text-[#202318] placeholder:text-[#707367] focus:outline-none focus:ring-2 focus:ring-[#006323]/20 focus:border-[#006323] transition-all shadow-xs"
          />
          <kbd className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[10px] font-bold text-[#707367] bg-[#f1f3ee] px-1.5 py-0.5 rounded border border-[#e9ebe3]">
            ⌘F
          </kbd>
        </div>

        {/* Right Notification & Profile */}
        <div className="flex items-center gap-2.5">
          <button 
            title="Messages"
            className="w-9 h-9 rounded-full border border-[#e9ebe3] bg-white flex items-center justify-center text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318] transition-all cursor-pointer"
          >
            <Mail className="w-4 h-4" />
          </button>

          <button 
            title="Notifications"
            className="w-9 h-9 rounded-full border border-[#e9ebe3] bg-white flex items-center justify-center text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318] transition-all relative cursor-pointer"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 animate-pulse ring-2 ring-white" />
          </button>

          {/* User Profile */}
          <div className="flex items-center gap-2.5 pl-3 border-l border-[#e9ebe3]">
            <div className="w-8 h-8 rounded-full bg-[#e6f7ec] border border-[#a7f3d0] flex items-center justify-center text-[#006323] font-bold text-xs">
              JS
            </div>
            <div className="hidden sm:block text-left leading-tight">
              <p className="text-xs font-bold text-[#202318]">Jessin Sam</p>
              <p className="text-[10px] text-[#707367]">Risk Operations Lead</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Title Row & Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-[#202318] tracking-tight">
            Fraud Operations Console
          </h1>
          <p className="text-xs lg:text-sm text-[#707367] mt-0.5 font-medium">
            Real-time Bayesian decisioning, online feature hydration & drift telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
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
