import React, { useState } from 'react';
import { ChevronRight, ShieldCheck, AlertTriangle, ShieldX, ChevronDown, ChevronUp } from 'lucide-react';
import type { TransactionItem } from '../types';

interface StreamFeedProps {
  transactions: TransactionItem[];
  selectedTxId: number | null;
  onSelectTransaction: (tx: TransactionItem) => void;
}

export const StreamFeed: React.FC<StreamFeedProps> = ({
  transactions,
  selectedTxId,
  onSelectTransaction,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getActionChip = (action: string) => {
    switch (action) {
      case 'APPROVE':
        return (
          <span className="bg-[#e6f7ec] text-[#006323] text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 border border-[#a7f3d0]">
            <ShieldCheck className="w-3 h-3" />
            Approved
          </span>
        );
      case 'STEP_UP_3DS':
        return (
          <span className="bg-[#fef7e6] text-[#b45309] text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 border border-[#fde68a]">
            <AlertTriangle className="w-3 h-3" />
            3DS Step-Up
          </span>
        );
      case 'DECLINE':
      default:
        return (
          <span className="bg-[#feecee] text-[#b91c1c] text-xs px-3 py-1 rounded-full font-bold inline-flex items-center gap-1 border border-[#fecaca]">
            <ShieldX className="w-3 h-3" />
            Declined
          </span>
        );
    }
  };

  const getAvatarInitials = (action: string) => {
    switch (action) {
      case 'APPROVE': return 'AP';
      case 'STEP_UP_3DS': return '3D';
      case 'DECLINE': return 'DC';
      default: return 'TX';
    }
  };

  const displayedTransactions = isExpanded ? transactions : transactions.slice(0, 3);

  return (
    <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-[#202318] tracking-tight">
            Recent Stream Forensics
          </h2>
          <p className="text-xs text-[#707367]">
            Click any row to inspect attribution and submit ground-truth chargeback feedback
          </p>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-8 px-3 rounded-lg border border-[#e9ebe3] text-xs font-semibold text-[#202318] hover:bg-[#f1f3ee] flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5 text-[#707367]" />
              <span>View Less</span>
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5 text-[#707367]" />
              <span>View More</span>
            </>
          )}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {transactions.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#707367]">
            Waiting for live transactions from Redpanda stream...
          </div>
        ) : (
          displayedTransactions.map((tx) => {
            const isSelected = selectedTxId === tx.transaction_id;
            return (
              <div
                key={tx.transaction_id}
                onClick={() => onSelectTransaction(tx)}
                className={`flex items-center justify-between p-3 rounded-xl transition-all duration-200 cursor-pointer border ${
                  isSelected
                    ? 'bg-[#f3fbf5] border-[#006323] ring-2 ring-[#006323]/20 shadow-xs'
                    : 'bg-white border-transparent hover:bg-[#f8f9f5] hover:border-[#e9ebe3]'
                }`}
              >
                {/* Left: Avatar & Metadata */}
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ring-2 ${
                    tx.action === 'APPROVE'
                      ? 'bg-[#e6f7ec] text-[#006323] ring-[#006323]/20'
                      : tx.action === 'STEP_UP_3DS'
                      ? 'bg-[#fef7e6] text-[#b45309] ring-amber-500/20'
                      : 'bg-[#feecee] text-[#b91c1c] ring-rose-500/20'
                  }`}>
                    {getAvatarInitials(tx.action)}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-[#202318] truncate">
                        ${tx.transaction_amount.toFixed(2)}
                      </p>
                      <span className="text-xs font-medium text-[#707367] mono-num">
                        • {tx.card_token}
                      </span>
                    </div>
                    <p className="text-xs text-[#707367] truncate mt-0.5">
                      P(Fraud): <span className="font-bold text-[#202318] mono-num">{(tx.fraud_probability * 100).toFixed(1)}%</span> • {tx.primary_reason}
                    </p>
                  </div>
                </div>

                {/* Right: Status Pill & Arrow */}
                <div className="flex items-center gap-3 shrink-0 ml-3">
                  {getActionChip(tx.action)}
                  <ChevronRight className={`w-4 h-4 text-[#707367] transition-transform ${isSelected ? 'rotate-90 text-[#006323]' : ''}`} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
