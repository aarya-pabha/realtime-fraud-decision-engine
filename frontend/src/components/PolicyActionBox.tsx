import React, { useState, useEffect } from 'react';
import { AlertCircle, ShieldAlert, CheckCircle2, ShieldCheck, Target, ShieldX, Clock } from 'lucide-react';
import type { TransactionItem } from '../types';

interface PolicyActionBoxProps {
  selectedTx: TransactionItem | null;
  onSubmitFeedback: (txId: number, isChargeback: boolean) => Promise<void>;
}

// Convert raw snake_case reason codes into human-readable banking terms
const formatReasonCode = (code: string): string => {
  const overrides: Record<string, string> = {
    HIGH_VELOCITY_ASSOCIATED_PHONE_COUNT: 'High-Velocity Phone Burst Count',
    RISK_INDICATOR_R_EMAILDOMAIN: 'High-Risk Recipient Email Domain',
    RISK_INDICATOR_P_EMAILDOMAIN: 'High-Risk Purchaser Email Domain',
    IRREGULAR_TRANSACTION_CYCLE_DELTA: 'Irregular Transaction Timing Cycle',
    UNUSUAL_TRANSACTION_AMOUNT: 'Unusual High-Value Purchase Amount',
    UNUSUAL_PAYMENT_COUNT_BURST: 'Rapid Payment Count Velocity Spike',
    HIGH_RISK_CARD_TYPE_CATEGORY: 'High-Risk Card & Product Category',
    HIGH_CROSS_MERCHANT_CARD_COUNT: 'High Cross-Merchant Card Activity',
    NORMAL_ACCOUNT_BEHAVIOR: 'Normal Behavioral Tenancy Baseline',
    LOW_RISK_TRANSACTION_AMOUNT: 'Low-Risk Standard Purchase Amount',
    VERIFIED_DEVICE_BASELINE: 'Verified Device & Browser Signature',
  };
  if (overrides[code]) return overrides[code];

  return code
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const PolicyActionBox: React.FC<PolicyActionBoxProps> = ({
  selectedTx,
  onSubmitFeedback,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [highlightKey, setHighlightKey] = useState<number | null>(null);
  const [challengeDispatched, setChallengeDispatched] = useState<boolean>(false);

  // Trigger attention highlight and reset challenge state when selectedTx changes
  useEffect(() => {
    if (selectedTx) {
      setHighlightKey(selectedTx.transaction_id);
      setChallengeDispatched(false);
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

  const getStatusTheme = (action: string) => {
    switch (action) {
      case 'APPROVE':
        return {
          container: 'bg-[#f4fbf6] border-[#d1fae5]',
          label: 'text-[#006323]',
          badge: 'bg-[#e6f7ec] text-[#006323] border-[#a7f3d0]',
          name: 'Approved'
        };
      case 'STEP_UP_3DS':
        return {
          container: 'bg-[#fffbeb] border-[#fde68a]',
          label: 'text-[#b45309]',
          badge: 'bg-[#fef7e6] text-[#b45309] border-[#fde68a]',
          name: '3DS Step-Up'
        };
      case 'DECLINE':
      default:
        return {
          container: 'bg-[#fef2f2] border-[#fecaca]',
          label: 'text-[#b91c1c]',
          badge: 'bg-[#feecee] text-[#b91c1c] border-[#fecaca]',
          name: 'Declined'
        };
    }
  };

  const statusTheme = selectedTx ? getStatusTheme(selectedTx.action) : null;

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

      {selectedTx && statusTheme ? (
        <div className="space-y-4">
          <div className={`border rounded-xl p-4 transition-all duration-300 hover:shadow-sm ${statusTheme.container}`}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold uppercase tracking-wider ${statusTheme.label}`}>
                  Target Transaction #{selectedTx.transaction_id}
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusTheme.badge}`}>
                  {statusTheme.name}
                </span>
              </div>
              <span className="text-xs font-bold text-[#202318] mono-num">
                ${(selectedTx.transaction_amount ?? 0).toFixed(2)}
              </span>
            </div>


            <p className="text-xs text-[#707367] mb-3 font-medium">
              Risk Probability: <span className="font-bold text-[#202318] mono-num">{((selectedTx.fraud_probability ?? 0) * 100).toFixed(1)}%</span> • {selectedTx.card_token}
            </p>

            <div className="bg-white border border-[#e9ebe3] rounded-xl p-3 mb-3 text-xs text-[#202318] shadow-xs">
              <span className="font-bold text-[#707367] block text-[10px] uppercase tracking-wider mb-1.5">
                {selectedTx.action === 'APPROVE' ? 'Model Attribution Status:' : 'Primary Risk Attribution (TreeSHAP):'}
              </span>
              {selectedTx.action === 'APPROVE' ? (
                <div>
                  <div className="flex items-center gap-1.5 font-bold text-[#006323]">
                    <ShieldCheck className="w-4 h-4 text-[#006323] shrink-0" />
                    <span>TreeSHAP Bypassed (Fast-Path Flow)</span>
                  </div>
                  <p className="text-[11px] text-[#707367] mt-1 leading-snug">
                    Clean baseline behavior. Adverse-action TreeSHAP attribution is conditionally evaluated only on 3DS step-ups and declines.
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <span className={`font-bold ${statusTheme.label}`}>
                    {formatReasonCode(selectedTx.primary_reason)}
                  </span>
                  <span className="text-[10px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-md">
                    +Risk Factor
                  </span>
                </div>
              )}
            </div>

            {/* Contextual Policy Action Button */}
            {selectedTx.action === 'APPROVE' ? (
              challengeDispatched ? (
                <div className="w-full h-10 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs font-bold flex items-center justify-center gap-2 shadow-xs animate-in fade-in duration-200">
                  <Clock className="w-4 h-4 text-amber-700" />
                  <span>3DS 2.0 Challenge Dispatched • SMS/OTP Sent</span>
                </div>
              ) : (
                <button
                  onClick={() => setChallengeDispatched(true)}
                  className="w-full h-10 rounded-xl bg-[#006323] text-white text-xs font-bold flex items-center justify-center gap-2 hover:bg-[#004d1b] transition-all shadow-md cursor-pointer"
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Escalate to 3DS Step-Up Challenge</span>
                </button>
              )
            ) : selectedTx.action === 'STEP_UP_3DS' ? (
              <div className="w-full h-10 rounded-xl bg-[#fffbeb] border border-[#fde68a] text-amber-900 text-xs font-bold flex items-center justify-center gap-2 shadow-xs">
                <ShieldAlert className="w-4 h-4 text-amber-700" />
                <span>3DS Challenge Active • Issuer Verification Pending</span>
              </div>
            ) : (
              <div className="w-full h-10 rounded-xl bg-[#f8f9f5] border border-[#e9ebe3] text-[#707367] text-xs font-bold flex items-center justify-center gap-2 shadow-xs cursor-not-allowed">
                <ShieldX className="w-4 h-4 text-rose-600" />
                <span>Hard Declined by Policy • 3DS Ineligible</span>
              </div>
            )}
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
