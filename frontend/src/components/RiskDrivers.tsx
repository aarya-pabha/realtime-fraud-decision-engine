import React from 'react';
import { DollarSign, Activity, Mail, Clock, Globe } from 'lucide-react';

export const RiskDrivers: React.FC = () => {
  const drivers = [
    {
      title: 'High Transaction Amount Skew',
      desc: 'Bayesian threshold dynamically tightens as dollar value escalates',
      icon: DollarSign,
      color: 'bg-blue-500',
      tag: 'Weight: +0.41',
    },
    {
      title: '5-Min Card Velocity Burst (C1)',
      desc: 'Repeated authorizations over short sliding window trigger step-up',
      icon: Activity,
      color: 'bg-amber-500',
      tag: 'Weight: +0.38',
    },
    {
      title: 'Disposable Email Domain Mismatch',
      desc: 'Temporary inbox paired with missing recipient billing token',
      icon: Mail,
      color: 'bg-[#006323]',
      tag: 'Weight: +0.29',
    },
    {
      title: 'Card Registration Tenure Delta (D1)',
      desc: 'New card lifecycle anomaly relative to historical baseline',
      icon: Clock,
      color: 'bg-purple-500',
      tag: 'Weight: +0.22',
    },
    {
      title: 'Cross-Border Billing Mismatch (addr2)',
      desc: 'Purchaser billing country differs from card issuer registry',
      icon: Globe,
      color: 'bg-cyan-500',
      tag: 'Weight: +0.19',
    },
  ];

  return (
    <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-[#202318] tracking-tight">
            Top SHAP Risk Attribution Factors
          </h2>
          <p className="text-xs text-[#707367]">
            Global feature weights driving localized banking reason codes
          </p>
        </div>
        <span className="text-xs font-bold text-[#707367] bg-[#f1f3ee] px-2.5 py-1 rounded-lg">
          TreeSHAP C++
        </span>
      </div>

      <div className="space-y-3">
        {drivers.map((d, i) => {
          const IconComponent = d.icon;
          return (
            <div
              key={i}
              className="flex items-center gap-3.5 p-3 rounded-xl hover:bg-[#f8f9f5] border border-transparent hover:border-[#e9ebe3] transition-all duration-200 cursor-pointer group"
            >
              <div className={`${d.color} w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0 shadow-xs transition-transform duration-300 group-hover:scale-105`}>
                <IconComponent className="w-5 h-5" />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-[#202318] truncate">
                  {d.title}
                </p>
                <p className="text-xs text-[#707367] truncate mt-0.5">
                  {d.desc}
                </p>
              </div>

              <span className="text-[10px] font-bold text-[#707367] bg-[#f1f3ee] px-2 py-1 rounded-md mono-num shrink-0">
                {d.tag}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
