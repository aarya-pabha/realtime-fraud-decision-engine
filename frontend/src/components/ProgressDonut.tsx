import type { StreamKpis } from '../types';

interface ProgressDonutProps {
  kpis: StreamKpis;
}

export const ProgressDonut: React.FC<ProgressDonutProps> = ({ kpis }) => {
  const radius = 62;
  const circumference = 2 * Math.PI * radius;
  const compliancePct = kpis.sla_compliance_pct || 99.8;
  const offset = circumference - (compliancePct / 100) * circumference;

  return (
    <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-bold text-[#202318] tracking-tight">
          SLA Compliance
        </h2>
        <span className="text-[11px] font-bold text-[#006323] bg-[#e6f7ec] px-2 py-0.5 rounded-full">
          Healthy
        </span>
      </div>

      {/* Donut Ring Visual */}
      <div className="flex flex-col items-center justify-center my-3">
        <div className="relative w-36 h-36">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
            {/* Background Track */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              stroke="#f1f3ee"
              strokeWidth="12"
              fill="none"
            />
            {/* Active Forest Green Arc */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              stroke="#006323"
              strokeWidth="12"
              fill="none"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
            />
          </svg>

          {/* Center Text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-3xl font-extrabold text-[#202318] mono-num">
              {compliancePct.toFixed(1)}%
            </span>
            <span className="text-[10px] font-bold text-[#707367] tracking-tight mt-0.5 uppercase">
              Sub-25ms SLA
            </span>
          </div>
        </div>
      </div>

      {/* Legend Chips */}
      <div className="flex items-center justify-center gap-4 text-xs font-semibold text-[#707367] pt-2 border-t border-[#f1f3ee]">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#006323]" />
          <span>Approved ({kpis.approval_rate_pct.toFixed(0)}%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span>3DS ({kpis.step_up_rate_pct.toFixed(0)}%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <span>Declined ({kpis.decline_rate_pct.toFixed(0)}%)</span>
        </div>
      </div>
    </div>
  );
};
