import React, { useState } from 'react';
import { X, Play } from 'lucide-react';
import type { SimulationPayload } from '../types';

interface ScenarioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSimulate: (payload: SimulationPayload) => Promise<void>;
}

export const ScenarioModal: React.FC<ScenarioModalProps> = ({
  isOpen,
  onClose,
  onSimulate,
}) => {
  const [amount, setAmount] = useState<number>(250);
  const [velocity, setVelocity] = useState<number>(1);
  const [productCode, setProductCode] = useState<string>('W');
  const [emailDomain, setEmailDomain] = useState<string>('gmail.com');
  const [loading, setLoading] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const isCrossBorderAttack = productCode === 'C' || velocity > 5 || emailDomain.includes('mailinator');
      await onSimulate({
        TransactionAmt: amount,
        ProductCD: productCode,
        card1: isCrossBorderAttack ? 8821 : (amount > 1000 ? 4242 : 10230),
        card4: isCrossBorderAttack ? 'mastercard' : 'visa',
        card6: isCrossBorderAttack || amount > 1000 ? 'credit' : 'debit',
        P_emaildomain: emailDomain,
        R_emaildomain: emailDomain.includes('mailinator') ? 'protonmail.com' : undefined,
        C1: velocity,
        tx_count_5m: velocity > 1 ? velocity : 0,
        tx_count_1h: velocity > 1 ? velocity * 3 : 1,
        amt_sum_24h: velocity > 1 ? amount * velocity : amount,
        TransactionDT: 86400,
      });
      onClose();
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (amt: number, vel: number, prod: string, email: string) => {
    setAmount(amt);
    setVelocity(vel);
    setProductCode(prod);
    setEmailDomain(email);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
      <div className="bg-white border border-[#e9ebe3] rounded-3xl w-full max-w-lg p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#f1f3ee]">
          <div>
            <h3 className="text-lg font-extrabold text-[#202318] tracking-tight">
              Simulate Live Transaction Authorization
            </h3>
            <p className="text-xs text-[#707367]">
              Injects parameters directly into FastAPI LightGBM + TreeSHAP + Router
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full border border-[#e9ebe3] flex items-center justify-center text-[#707367] hover:bg-[#f1f3ee] hover:text-[#202318] transition-all cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 1-Click Quick Presets */}
        <div className="mb-5">
          <p className="text-[10px] font-bold text-[#707367] uppercase tracking-wider mb-2">
            1-Click Attack Presets
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => applyPreset(25, 1, 'W', 'gmail.com')}
              className="p-2 rounded-xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-[#e6f7ec] hover:border-[#a7f3d0] text-left transition-all cursor-pointer"
            >
              <span className="text-xs font-bold text-[#006323] block">Baseline</span>
              <span className="text-[10px] text-[#707367]">$25 • 1 tx</span>
            </button>

            <button
              type="button"
              onClick={() => applyPreset(2400, 1, 'H', 'anonymous.com')}
              className="p-2 rounded-xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-[#fef7e6] hover:border-[#fde68a] text-left transition-all cursor-pointer"
            >
              <span className="text-xs font-bold text-amber-700 block">High-Value</span>
              <span className="text-[10px] text-[#707367]">$2,400 • Tech</span>
            </button>

            <button
              type="button"
              onClick={() => applyPreset(150, 14, 'C', 'mailinator.com')}
              className="p-2 rounded-xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-rose-50 hover:border-rose-200 text-left transition-all cursor-pointer"
            >
              <span className="text-xs font-bold text-rose-700 block">Card-Burst</span>
              <span className="text-[10px] text-[#707367]">$150 • 14 tx</span>
            </button>
          </div>
        </div>

        {/* Form Controls */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Amount Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label htmlFor="simulation-amount-slider" className="text-xs font-bold text-[#202318]">
                Transaction Amount ($ USD)
              </label>
              <span className="text-sm font-bold text-[#006323] mono-num">
                ${amount.toFixed(2)}
              </span>
            </div>
            <input
              id="simulation-amount-slider"
              name="simulation-amount-slider"
              aria-label="Transaction Amount ($ USD)"
              type="range"
              min={10}
              max={4000}
              step={25}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full h-2 bg-[#f1f3ee] rounded-lg appearance-none cursor-pointer accent-[#006323]"
            />
            <div className="flex justify-between text-[10px] text-[#707367] mono-num mt-1">
              <span>$10</span>
              <span>$1,000</span>
              <span>$2,500</span>
              <span>$4,000</span>
            </div>
          </div>

          {/* Velocity Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label htmlFor="simulation-velocity-slider" className="text-xs font-bold text-[#202318]">
                Card Velocity (5-Min Authorizations)
              </label>
              <span className="text-sm font-bold text-amber-600 mono-num">
                {velocity} tx / 5m
              </span>
            </div>
            <input
              id="simulation-velocity-slider"
              name="simulation-velocity-slider"
              aria-label="Card Velocity (5-Min Authorizations)"
              type="range"
              min={0}
              max={20}
              step={1}
              value={velocity}
              onChange={(e) => setVelocity(Number(e.target.value))}
              className="w-full h-2 bg-[#f1f3ee] rounded-lg appearance-none cursor-pointer accent-amber-600"
            />
            <div className="flex justify-between text-[10px] text-[#707367] mono-num mt-1">
              <span>0 (Single)</span>
              <span>10 (High)</span>
              <span>20 (Burst)</span>
            </div>
          </div>

          {/* Product Category */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="simulation-product-category" className="text-xs font-bold text-[#202318] block mb-1">
                Product Category
              </label>
              <select
                id="simulation-product-category"
                name="simulation-product-category"
                value={productCode}
                onChange={(e) => setProductCode(e.target.value)}
                className="w-full h-9 px-3 rounded-xl border border-[#e9ebe3] bg-white text-xs font-semibold text-[#202318] focus:outline-none focus:border-[#006323]"
              >
                <option value="W">W — Domestic Retail</option>
                <option value="C">C — Cross-Border</option>
                <option value="H">H — High-Tech Hardware</option>
                <option value="R">R — Recurring Subscription</option>
              </select>
            </div>

            <div>
              <label htmlFor="simulation-email-domain" className="text-xs font-bold text-[#202318] block mb-1">
                Email Domain Profile
              </label>
              <select
                id="simulation-email-domain"
                name="simulation-email-domain"
                value={emailDomain}
                onChange={(e) => setEmailDomain(e.target.value)}
                className="w-full h-9 px-3 rounded-xl border border-[#e9ebe3] bg-white text-xs font-semibold text-[#202318] focus:outline-none focus:border-[#006323]"
              >
                <option value="gmail.com">gmail.com (Verified)</option>
                <option value="anonymous.com">anonymous.com (Mismatch)</option>
                <option value="mailinator.com">mailinator.com (Disposable)</option>
              </select>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 rounded-xl bg-[#006323] hover:bg-[#004d1b] text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg transition-all cursor-pointer mt-2 disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{loading ? 'Evaluating via LightGBM...' : 'Score Transaction Instantly'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
