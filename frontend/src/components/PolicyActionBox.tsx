import React, { useState, useEffect } from 'react';
import { AlertCircle, ShieldAlert, CheckCircle2, ShieldCheck, Target } from 'lucide-react';
import type { TransactionItem } from '../types';

interface PolicyActionBoxProps {
  selectedTx: TransactionItem | null;
  onSubmitFeedback: (txId: number, isChargeback: boolean) => Promise<void>;
}

export const PolicyActionBox: React.FC<PolicyActionBoxProps> = ({
  selectedTx,
  onSubmitFeedback,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [highlightKey, setHighlightKey] = useState<number | null>(null);

  // Trigger attention highlight when selectedTx changes
  useEffect(() => {
    if (selectedTx) {
      setHighlightKey(selectedTx.transaction_id);
      const timer = setTimeout(() => setHighlightKey(null), 1200);
      return () => clearTimeout(timer);
    }
  }, [selectedTx?.transaction_id]);

  const handleFeedback = async (isChargeback: boolean) => {
    if (!selectedTx) return;
    setSubmitting(true);
    try {
      await onSubmitFeedback(selectedTx.transaction_id, isChargeback);
      setFeedbackSuccess(isChargeback ? 'Flagged as Chargeback' : 'Confirmed Legitimate');
      setTimeout(() => setFeedbackSuccess(null), 3000);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`bg-white border rounded-2xl p-6 shadow-xs hover:shadow-md transition-all duration-300 ${
      highlightKey ? 'border-[#006323] ring-2 ring-[#006323]/20 shadow-md' : 'border-[#e9ebe3]'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold text-[#202318] tracking-tight flex items-center gap-2">
          <Target className="w-4 h-4 text-[#006323]" />
          Selected Transaction Forensics & Actions
        </h2>
      </div>

      {selectedTx ? (
        <div className="space-y-4">
          <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4 transition-all duration-300 hover:shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-[#006323] uppercase tracking-wider">
                Target Transaction #{selectedTx.transaction_id}
              </span>
              <span className="text-xs font-bold text-[#202318] mono-num">
                ${selectedTx.transaction_amount.toFixed(2)}
              </span>
            </div>

            <p className="text-xs text-[#707367] mb-3 font-medium">
              Risk Probability: <span className="font-bold text-[#202318] mono-num">{(selectedTx.fraud_probability * 100).toFixed(1)}%</span> • {selectedTx.card_token}
            </p>

            <div className="bg-white border border-[#e9ebe3] rounded-lg p-2.5 mb-3 text-xs text-[#202318]">
              <span className="font-bold text-[#707367] block text-[10px] uppercase tracking-wide mb-1">
                Primary Factor Attribution:
              </span>
              <p className="font-semibold text-[#006323]">
                {selectedTx.primary_reason}
              </p>
            </div>

            <button
              onClick={() => handleFeedback(true)}
              disabled={submitting}
              className="w-full h-10 rounded-xl bg-[#006323] text-white text-xs font-bold flex items-center justify-center gap-2 hover:bg-[#004d1b] transition-all shadow-md cursor-pointer disabled:opacity-50"
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Trigger 3DS Step-Up Challenge</span>
            </button>
          </div>

          {/* Dispute Feedback Loop */}
          <div className="pt-2">
            <p className="text-xs font-bold text-[#202318] mb-1">
              Analyst Ground-Truth Feedback Station
            </p>
            <p className="text-[11px] text-[#707367] mb-2.5">
              Submits verified chargeback labels to update Evidently AI stability distributions:
            </p>

            {feedbackSuccess && (
              <div className="mb-2.5 p-2 rounded-lg bg-[#e6f7ec] border border-[#a7f3d0] text-[#006323] text-xs font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{feedbackSuccess}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleFeedback(true)}
                disabled={submitting}
                className="h-9 rounded-xl border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
              >
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Flag Dispute</span>
              </button>

              <button
                onClick={() => handleFeedback(false)}
                disabled={submitting}
                className="h-9 rounded-xl border border-[#e9ebe3] bg-white hover:bg-[#f1f3ee] text-[#202318] text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-xs"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#006323]" />
                <span>Mark Legit</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 text-center bg-[#f8f9f5] rounded-xl border border-[#e9ebe3] text-xs text-[#707367]">
          Select any transaction from the stream table to inspect dynamic decision attributes and trigger policy interventions.
        </div>
      )}
    </div>
  );
};
