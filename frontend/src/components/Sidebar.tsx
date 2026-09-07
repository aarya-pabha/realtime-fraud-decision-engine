import React from 'react';
import { 
  LayoutDashboard, 
  SquareCheckBig, 
  ShieldAlert, 
  ShieldCheck,
  Zap
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  streamOnline: boolean;
  avgLatencyMs?: number;
  p95LatencyMs?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  activeTab, 
  setActiveTab, 
  streamOnline,
  avgLatencyMs = 24.11,
  p95LatencyMs = 23.46,
}) => {
  return (
    <aside className="w-64 bg-[#f8f9f5] border-r border-[#e9ebe3] p-5 h-screen flex flex-col justify-between fixed top-0 left-0 z-30 select-none overflow-y-auto">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3 mb-6 px-1">
          <div className="w-9 h-9 rounded-xl bg-[#006323] flex items-center justify-center text-white shadow-sm shadow-[#006323]/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="leading-tight">
            <span className="text-lg font-extrabold text-[#202318] tracking-tight block">
              FraudEngine
            </span>
            <span className="text-[10px] font-bold text-[#006323] tracking-wide uppercase block">
              Decision Platform
            </span>
          </div>
        </div>

        {/* Menu Navigation */}
        <div className="mb-6">
          <p className="text-[10px] font-bold text-[#707367] uppercase tracking-wider mb-2 px-3">
            Menu
          </p>
          <nav className="flex flex-col gap-1.5">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'dashboard'
                  ? 'bg-[#006323] text-white shadow-lg shadow-[#006323]/25 font-bold'
                  : 'text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeTab === 'dashboard' ? 'bg-white/20 text-white' : 'bg-[#e6f7ec] text-[#006323]'
              }`}>
                Live
              </span>
            </button>

            <button
              onClick={() => setActiveTab('simulator')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'simulator'
                  ? 'bg-[#006323] text-white shadow-lg shadow-[#006323]/25 font-bold'
                  : 'text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <SquareCheckBig className="w-4 h-4" />
                <span>3DS Simulator</span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeTab === 'simulator' ? 'bg-white/20 text-white' : 'bg-[#f1f3ee] text-[#707367]'
              }`}>
                Sandbox
              </span>
            </button>

            <button
              onClick={() => setActiveTab('drift')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
                activeTab === 'drift'
                  ? 'bg-[#006323] text-white shadow-lg shadow-[#006323]/25 font-bold'
                  : 'text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-4 h-4" />
                <span>Drift & Stability</span>
              </div>
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                activeTab === 'drift' ? 'bg-white/20 text-white' : 'bg-[#f1f3ee] text-[#707367]'
              }`}>
                Evidently
              </span>
            </button>
          </nav>
        </div>
      </div>

      {/* Telemetry Cockpit Section */}
      <div className="flex flex-col gap-3 pt-3 border-t border-[#e9ebe3]">
        {/* Real-Time Engine SLA Card */}
        <div className="bg-[#111827] text-white rounded-xl p-3.5 border border-[#1f2937] shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${streamOnline ? 'bg-emerald-400' : 'bg-amber-400'} opacity-75`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${streamOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              </span>
              <span className="text-[10px] font-extrabold text-emerald-400 uppercase tracking-wider">
                Engine SLA
              </span>
            </div>
            <span className="text-[9px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full">
              p95 &lt; 25ms
            </span>
          </div>
          <div className="text-2xl font-black tracking-tight mono-num text-white my-1">
            {avgLatencyMs.toFixed(2)} <span className="text-xs font-normal text-gray-400">ms</span>
          </div>
          <p className="text-[10px] text-gray-400 font-medium">
            p95: {p95LatencyMs.toFixed(2)} ms • Single-pass LightGBM
          </p>
        </div>

        {/* Top Risk Drivers Card */}
        <div className="bg-white border border-[#e9ebe3] rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-[10px] font-bold text-[#707367] uppercase tracking-wider flex items-center gap-1">
              <Zap className="w-3 h-3 text-[#006323]" />
              Top Risk Drivers
            </span>
            <span className="text-[9px] font-extrabold text-[#006323] bg-[#e6f7ec] px-1.5 py-0.5 rounded-md border border-[#a7f3d0]">
              TreeSHAP
            </span>
          </div>
          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">Transaction Amount</span>
              <span className="text-[10px] font-bold text-[#b45309] bg-[#fef7e6] border border-[#fde68a] px-1.5 py-0.2 rounded-full mono-num">+0.41</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">5m Card Velocity</span>
              <span className="text-[10px] font-bold text-[#b45309] bg-[#fef7e6] border border-[#fde68a] px-1.5 py-0.2 rounded-full mono-num">+0.38</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">Disposable Email</span>
              <span className="text-[10px] font-bold text-[#b91c1c] bg-[#feecee] border border-[#fecaca] px-1.5 py-0.2 rounded-full mono-num">+0.29</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#202318] truncate">Account Tenancy</span>
              <span className="text-[10px] font-bold text-[#707367] bg-[#f1f3ee] border border-[#e9ebe3] px-1.5 py-0.2 rounded-full mono-num">+0.22</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
