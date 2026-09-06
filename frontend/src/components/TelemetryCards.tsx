import React from 'react';
import { Cpu, Play, Pause, RefreshCw, Zap, ShieldCheck } from 'lucide-react';
import type { StreamKpis } from '../types';

interface TelemetryCardsProps {
  kpis: StreamKpis;
  isPaused: boolean;
  onTogglePause: () => void;
  onResetBuffer: () => void;
  onSimulatePreset: (presetName: string) => void;
}

export const TelemetryCards: React.FC<TelemetryCardsProps> = ({
  kpis,
  isPaused,
  onTogglePause,
  onResetBuffer,
  onSimulatePreset,
}) => {
  return (
    <>
      {/* Dark Card 1: Dynamic Cost Router Strategy */}
      <div className="bg-[#18181b] text-white rounded-2xl p-6 shadow-lg relative overflow-hidden flex flex-col justify-between min-h-[300px]">
        {/* Wavy Ambient Background Vector */}
        <div className="absolute bottom-0 left-0 right-0 h-28 overflow-hidden pointer-events-none opacity-25">
          <svg className="absolute bottom-0 w-full h-full" viewBox="0 0 200 60" preserveAspectRatio="none">
            <path d="M0,30 Q25,15 50,30 T100,30 T150,30 T200,30 L200,60 L0,60 Z" fill="#006323" />
            <path d="M0,40 Q25,25 50,40 T100,40 T150,40 T200,40 L200,60 L0,60 Z" fill="#00a86b" />
          </svg>
        </div>

        <div className="relative z-10">
          <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center mb-3">
            <Cpu className="w-5 h-5 text-emerald-400" />
          </div>
          <h2 className="text-xl font-extrabold mb-1 tracking-tight">
            Dynamic Cost Router
          </h2>
          <p className="text-xs text-white/70 mb-3 leading-relaxed">
            Value-aware Bayesian decision boundary adapting dynamically:
          </p>

          <div className="bg-white/5 border border-white/10 rounded-xl p-3 mb-4">
            <p className="text-[11px] font-mono text-emerald-300">
              τ*(Amt) = (0.02·Amt + 5.0) / (1.02·Amt + 30.0)
            </p>
            <p className="text-[10px] text-white/60 mt-1">
              Decline multiplier k=4.0 • Zero unnecessary friction on low values
            </p>
          </div>
        </div>

        <div className="relative z-10 flex flex-col gap-2">
          <button
            onClick={() => onSimulatePreset('attack')}
            className="w-full h-10 rounded-xl bg-white text-[#18181b] hover:bg-white/90 text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md"
          >
            <Zap className="w-3.5 h-3.5 text-amber-600 fill-amber-600" />
            <span>Simulate Card Velocity Burst ($45.00)</span>
          </button>

          <button
            onClick={() => onSimulatePreset('highval')}
            className="w-full h-10 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Simulate High-Value Checkout ($2,400)</span>
          </button>
        </div>
      </div>

      {/* Dark Card 2: Sub-Millisecond SLA Latency Meter */}
      <div className="bg-[#18181b] text-white rounded-2xl p-6 shadow-lg relative overflow-hidden flex flex-col justify-between min-h-[300px]">
        {/* Subtle Wave Lines in Background */}
        <div className="absolute top-0 right-0 w-48 h-full opacity-15 pointer-events-none">
          <svg className="w-full h-full" viewBox="0 0 100 50" preserveAspectRatio="none">
            <path d="M0,25 Q12.5,10 25,25 T50,25 T75,25 T100,25" fill="none" stroke="#00a86b" strokeWidth="2" />
            <path d="M0,35 Q12.5,20 25,35 T50,35 T75,35 T100,35" fill="none" stroke="#006323" strokeWidth="2" />
          </svg>
        </div>

        <div className="relative z-10">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
            Real-Time Engine SLA
          </span>
          <h2 className="text-xl font-extrabold mt-1 mb-1 tracking-tight">
            Inference Telemetry
          </h2>
          <p className="text-xs text-white/70 mb-4">
            Unified single-pass LightGBM & TreeSHAP C++ runtime
          </p>

          <div className="text-4xl sm:text-5xl font-mono font-bold tracking-tight text-white mb-2 mono-num">
            {kpis.p95_latency_ms ? `${kpis.p95_latency_ms < 10 ? '0' : ''}${kpis.p95_latency_ms.toFixed(2)}` : '01.42'} <span className="text-xl text-emerald-400 font-normal">ms</span>
          </div>
          <p className="text-[11px] text-white/60">
            Current p95 latency against &lt;25.00 ms contractual SLA
          </p>
        </div>

        <div className="relative z-10 flex items-center gap-3 pt-4 border-t border-white/10">
          <button
            onClick={onTogglePause}
            className="h-10 px-4 rounded-xl bg-white text-[#18181b] hover:bg-white/90 text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-md"
          >
            {isPaused ? <Play className="w-3.5 h-3.5 fill-current" /> : <Pause className="w-3.5 h-3.5 fill-current" />}
            <span>{isPaused ? 'Resume Stream' : 'Pause Stream'}</span>
          </button>

          <button
            onClick={onResetBuffer}
            title="Reset Buffer"
            className="w-10 h-10 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 text-white flex items-center justify-center transition-all cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  );
};
