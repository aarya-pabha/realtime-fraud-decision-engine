import React from 'react';
import { 
  LayoutDashboard, 
  SquareCheckBig, 
  ShieldAlert, 
  ShieldCheck
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  streamOnline: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, streamOnline }) => {
  return (
    <aside className="w-64 bg-[#f8f9f5] border-r border-[#e9ebe3] p-5 h-screen flex flex-col justify-between fixed top-0 left-0 z-30 select-none">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3 mb-8 px-1">
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

        {/* Menu Section */}
        <div>
          <p className="text-[10px] font-bold text-[#707367] uppercase tracking-wider mb-2.5 px-3">
            Menu
          </p>
          <nav className="flex flex-col gap-1.5">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
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
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
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
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
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

      {/* Bottom Health Status Widget */}
      <div className="bg-white border border-[#e9ebe3] rounded-2xl p-4 shadow-xs">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${streamOnline ? 'bg-[#006323]' : 'bg-amber-500'} opacity-75`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${streamOnline ? 'bg-[#006323]' : 'bg-amber-500'}`} />
          </span>
          <span className="text-[11px] font-extrabold text-[#006323] uppercase tracking-wider">
            {streamOnline ? 'Engine Online' : 'Connecting...'}
          </span>
        </div>
        <p className="text-xs font-semibold text-[#202318] mb-0.5">LightGBM + TreeSHAP Active</p>
        <p className="text-[10px] text-[#707367] font-medium">Sub-25ms SLA Operational</p>
      </div>
    </aside>
  );
};
