import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';
import type { StreamKpis } from '../types';

interface AnalyticsChartProps {
  kpis: StreamKpis;
}

const mockHourlyData = [
  { time: '12:00', volume: 142, approved: 138, challenged: 4 },
  { time: '13:00', volume: 189, approved: 182, challenged: 7 },
  { time: '14:00', volume: 220, approved: 212, challenged: 8 },
  { time: '15:00', volume: 310, approved: 298, challenged: 12 },
  { time: '16:00', volume: 275, approved: 265, challenged: 10 },
  { time: '17:00', volume: 340, approved: 331, challenged: 9 },
  { time: '18:00', volume: 412, approved: 399, challenged: 13 },
  { time: '19:00', volume: 380, approved: 368, challenged: 12 },
  { time: '20:00', volume: 290, approved: 281, challenged: 9 },
];

export const AnalyticsChart: React.FC<AnalyticsChartProps> = ({ kpis }) => {
  return (
    <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300 flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-[#202318] tracking-tight">
              Decision Volume & Latency Analytics
            </h2>
            <p className="text-xs text-[#707367]">
              Rolling 24-hour authorization throughput & dynamic policy resolutions
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#707367]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#006323] animate-pulse" />
            <span>Live Stream Active</span>
          </div>
        </div>

        {/* Chart Area */}
        <div className="h-60 w-full mb-3">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockHourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f3ee" vertical={false} />
              <XAxis 
                dataKey="time" 
                tick={{ fill: '#707367', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                axisLine={{ stroke: '#e9ebe3' }}
                tickLine={false}
              />
              <YAxis 
                tick={{ fill: '#707367', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#ffffff', 
                  borderColor: '#e9ebe3', 
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                  fontSize: '12px',
                  fontWeight: '600'
                }}
                cursor={{ fill: 'rgba(0, 99, 35, 0.04)' }}
              />
              <Bar 
                dataKey="approved" 
                name="Direct Approvals" 
                fill="#006323" 
                radius={[4, 4, 0, 0]} 
              />
              <Bar 
                dataKey="challenged" 
                name="3DS Challenges" 
                fill="#00a86b" 
                radius={[4, 4, 0, 0]} 
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Footer Metrics */}
      <div className="pt-4 border-t border-[#f1f3ee] flex items-center justify-between text-xs font-medium">
        <div>
          <span className="text-[#707367]">Average Engine Latency: </span>
          <span className="font-bold text-[#202318] mono-num">{kpis.avg_latency_ms} ms</span>
        </div>
        <div>
          <span className="text-[#707367]">Peak p95 SLA: </span>
          <span className="font-bold text-[#006323] mono-num">{kpis.p95_latency_ms} ms</span>
          <span className="text-[10px] text-[#707367] ml-1">(&lt;25ms Target)</span>
        </div>
      </div>
    </div>
  );
};
