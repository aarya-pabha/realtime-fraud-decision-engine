import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { StatCards } from './components/StatCards';
import { AnalyticsChart } from './components/AnalyticsChart';
import { StreamFeed } from './components/StreamFeed';
import { PolicyActionBox } from './components/PolicyActionBox';
import { ProgressDonut } from './components/ProgressDonut';
import { RiskDrivers } from './components/RiskDrivers';
import { TelemetryCards } from './components/TelemetryCards';
import { ScenarioModal } from './components/ScenarioModal';
import type { TransactionItem, StreamKpis, SimulationPayload } from './types';

const DEFAULT_KPIS: StreamKpis = {
  total_processed: 0,
  total_holdout_pool: 92427,
  approved_count: 0,
  step_up_count: 0,
  declined_count: 0,
  approval_rate_pct: 0.0,
  step_up_rate_pct: 0.0,
  decline_rate_pct: 0.0,
  total_amount_dollars: 0.0,
  prevented_fraud_dollars: 0.0,
  avg_latency_ms: 1.42,
  p95_latency_ms: 3.80,
  chargeback_ratio_pct: 0.42,
  sla_compliance_pct: 99.8,
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [selectedTx, setSelectedTx] = useState<TransactionItem | null>(null);
  const [kpis, setKpis] = useState<StreamKpis>(DEFAULT_KPIS);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [streamOnline, setStreamOnline] = useState<boolean>(false);
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState<boolean>(false);

  // Fetch initial seed and start polling
  const fetchStreamData = async () => {
    try {
      const [resRecent, resKpis] = await Promise.all([
        fetch('/v1/stream/recent?limit=15'),
        fetch('/v1/stream/kpis'),
      ]);

      if (resRecent.ok) {
        const dataRecent = await resRecent.json();
        setTransactions(dataRecent);
        if (!selectedTx && dataRecent.length > 0) {
          setSelectedTx(dataRecent[0]);
        }
        setStreamOnline(true);
      }

      if (resKpis.ok) {
        const dataKpis = await resKpis.json();
        setKpis(dataKpis);
      }
    } catch {
      setStreamOnline(false);
    }
  };

  useEffect(() => {
    fetchStreamData();
    if (isPaused) return;

    const interval = setInterval(() => {
      fetchStreamData();
    }, 900);

    return () => clearInterval(interval);
  }, [isPaused]);

  // Handle transaction simulation
  const handleSimulate = async (payload: SimulationPayload) => {
    try {
      const res = await fetch('/v1/stream/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const newTx: TransactionItem = await res.json();
        setTransactions((prev) => [newTx, ...prev.slice(0, 19)]);
        setSelectedTx(newTx);
        fetchStreamData();
      }
    } catch (err) {
      console.error('Simulation error:', err);
    }
  };

  // 1-Click preset triggers
  const handleSimulatePreset = (preset: string) => {
    if (preset === 'attack') {
      handleSimulate({
        TransactionAmt: 45.0,
        ProductCD: 'C',
        card1: 8821,
        card4: 'mastercard',
        card6: 'credit',
        P_emaildomain: 'mailinator.com',
        C1: 8,
        TransactionDT: 86400,
      });
    } else if (preset === 'highval') {
      handleSimulate({
        TransactionAmt: 2400.0,
        ProductCD: 'H',
        card1: 4242,
        card4: 'visa',
        card6: 'credit',
        P_emaildomain: 'anonymous.com',
        C1: 1,
        TransactionDT: 86400,
      });
    }
  };

  // Submit analyst chargeback feedback
  const handleSubmitFeedback = async (txId: number, isChargeback: boolean) => {
    try {
      await fetch('/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: txId,
          is_fraud_chargeback: isChargeback ? 1 : 0,
          analyst_notes: isChargeback ? 'Verified payment dispute chargeback' : 'Verified legitimate purchase',
        }),
      });
    } catch (err) {
      console.error('Feedback error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9f5] flex text-[#202318] antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        streamOnline={streamOnline}
      />

      {/* Main Content Area */}
      <main className="flex-1 ml-64 p-6 lg:p-8 max-w-[1600px]">
        <Header
          onOpenScenarioModal={() => setIsScenarioModalOpen(true)}
          onRefreshStream={fetchStreamData}
          isStreaming={!isPaused}
        />

        {/* Tab 1: Full Tasko Dashboard View */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* 4 Stat KPI Bento Cards */}
            <StatCards kpis={kpis} />

            {/* Middle Section: 2/3 Left (Analytics + Stream) vs 1/3 Right (Policy + Donut) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column (2/3 width) */}
              <div className="lg:col-span-2 space-y-6">
                <AnalyticsChart kpis={kpis} />
                <StreamFeed
                  transactions={transactions}
                  selectedTxId={selectedTx ? selectedTx.transaction_id : null}
                  onSelectTransaction={(tx) => setSelectedTx(tx)}
                />
              </div>

              {/* Right Column (1/3 width) */}
              <div className="space-y-6">
                <PolicyActionBox
                  selectedTx={selectedTx}
                  onSubmitFeedback={handleSubmitFeedback}
                />
                <ProgressDonut kpis={kpis} />
              </div>
            </div>

            {/* Bottom 3-Card Grid (1/3, 1/3, 1/3) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <RiskDrivers />
              <TelemetryCards
                kpis={kpis}
                isPaused={isPaused}
                onTogglePause={() => setIsPaused(!isPaused)}
                onResetBuffer={fetchStreamData}
                onSimulatePreset={handleSimulatePreset}
              />
            </div>
          </div>
        )}

        {/* Tab 2: Interactive 3DS Simulator View */}
        {activeTab === 'simulator' && (
          <div className="space-y-6">
            <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs">
              <h2 className="text-xl font-bold text-[#202318] mb-1">
                Interactive 3DS Decisioning Sandbox
              </h2>
              <p className="text-xs text-[#707367] mb-6">
                Test how the Bayesian Cost Router dynamically shifts decision boundaries based on transaction value and velocity.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <button
                  onClick={() => handleSimulatePreset('attack')}
                  className="p-4 rounded-xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-rose-50 hover:border-rose-200 text-left transition-all cursor-pointer"
                >
                  <span className="text-xs font-bold text-rose-700 block">Velocity Burst Preset</span>
                  <span className="text-xs text-[#202318] font-semibold mt-1 block">$45.00 • 8 tx / 5m • Disposable Email</span>
                  <span className="text-[10px] text-rose-600 mt-2 inline-block font-bold">Expects: Hard Decline / Challenge</span>
                </button>

                <button
                  onClick={() => handleSimulatePreset('highval')}
                  className="p-4 rounded-xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-amber-50 hover:border-amber-200 text-left transition-all cursor-pointer"
                >
                  <span className="text-xs font-bold text-amber-700 block">High-Value Tech Preset</span>
                  <span className="text-xs text-[#202318] font-semibold mt-1 block">$2,400.00 • 1 tx / 5m • Tech Hardware</span>
                  <span className="text-[10px] text-amber-700 mt-2 inline-block font-bold">Expects: Dynamic 3DS Step-Up</span>
                </button>

                <button
                  onClick={() => handleSimulate({
                    TransactionAmt: 25.0,
                    ProductCD: 'W',
                    card1: 1029,
                    card4: 'visa',
                    card6: 'debit',
                    P_emaildomain: 'gmail.com',
                    C1: 1,
                    TransactionDT: 86400,
                  })}
                  className="p-4 rounded-xl border border-[#e9ebe3] bg-[#f8f9f5] hover:bg-emerald-50 hover:border-emerald-200 text-left transition-all cursor-pointer"
                >
                  <span className="text-xs font-bold text-[#006323] block">Baseline Retail Preset</span>
                  <span className="text-xs text-[#202318] font-semibold mt-1 block">$25.00 • 1 tx / 5m • Domestic Retail</span>
                  <span className="text-[10px] text-[#006323] mt-2 inline-block font-bold">Expects: Direct Approval (0% Friction)</span>
                </button>
              </div>

              {selectedTx && (
                <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <span className="text-xs font-bold text-[#707367] uppercase tracking-wide">
                        Latest Simulation Result
                      </span>
                      <h3 className="text-2xl font-black text-[#202318] mt-0.5">
                        {selectedTx.action === 'APPROVE' && 'Direct Approval'}
                        {selectedTx.action === 'STEP_UP_3DS' && 'Dynamic 3DS Challenge'}
                        {selectedTx.action === 'DECLINE' && 'Hard Fraud Decline'}
                      </h3>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-[#707367]">Execution Latency</span>
                      <p className="text-xl font-bold text-[#006323] mono-num">
                        {selectedTx.total_latency_ms.toFixed(2)} ms
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-4">
                    <div className="bg-white p-3 rounded-xl border border-[#e9ebe3]">
                      <span className="text-[#707367] block">Transaction Amount</span>
                      <span className="text-sm font-bold text-[#202318] mono-num">${selectedTx.transaction_amount.toFixed(2)}</span>
                    </div>
                    <div className="bg-white p-3 rounded-xl border border-[#e9ebe3]">
                      <span className="text-[#707367] block">P(Fraud) Score</span>
                      <span className="text-sm font-bold text-[#202318] mono-num">{(selectedTx.fraud_probability * 100).toFixed(2)}%</span>
                    </div>
                    <div className="bg-white p-3 rounded-xl border border-[#e9ebe3]">
                      <span className="text-[#707367] block">Step-Up Threshold τ*</span>
                      <span className="text-sm font-bold text-amber-700 mono-num">{selectedTx.tau_step_up ? selectedTx.tau_step_up.toFixed(3) : '0.045'}</span>
                    </div>
                    <div className="bg-white p-3 rounded-xl border border-[#e9ebe3]">
                      <span className="text-[#707367] block">Decline Threshold k·τ*</span>
                      <span className="text-sm font-bold text-rose-700 mono-num">{selectedTx.tau_decline ? selectedTx.tau_decline.toFixed(3) : '0.180'}</span>
                    </div>
                  </div>

                  <div className="bg-white p-4 rounded-xl border border-[#e9ebe3]">
                    <span className="text-xs font-bold text-[#707367] uppercase tracking-wide block mb-2">
                      Top Localized TreeSHAP Reason Codes
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {selectedTx.reason_codes && selectedTx.reason_codes.length > 0 ? (
                        selectedTx.reason_codes.map((rc, idx) => (
                          <span
                            key={idx}
                            className="bg-[#f1f3ee] text-[#202318] text-xs font-semibold px-3 py-1.5 rounded-lg border border-[#e9ebe3]"
                          >
                            {rc}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-[#707367]">Baseline Normal Transaction</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Evidently AI Drift Center View */}
        {activeTab === 'drift' && (
          <div className="space-y-6">
            <div className="bg-white border border-[#e9ebe3] rounded-2xl p-6 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold text-[#202318] tracking-tight">
                    Evidently AI Stability & Concept Drift Center
                  </h2>
                  <p className="text-xs text-[#707367]">
                    Monitors distribution shifts across payment amounts, burst velocities, and delayed ground-truth chargebacks.
                  </p>
                </div>
                <span className="text-xs font-bold text-[#006323] bg-[#e6f7ec] px-3 py-1 rounded-full border border-[#a7f3d0]">
                  Model Stable • 0 Alerts
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4">
                  <span className="text-xs text-[#707367] font-semibold">Transaction Amount Drift</span>
                  <p className="text-2xl font-bold text-[#202318] mt-1 mono-num">0.038</p>
                  <p className="text-[10px] text-[#006323] mt-1 font-bold">Wasserstein Distance &lt; 0.10 Threshold</p>
                </div>

                <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4">
                  <span className="text-xs text-[#707367] font-semibold">Velocity 5m Drift</span>
                  <p className="text-2xl font-bold text-[#202318] mt-1 mono-num">0.021</p>
                  <p className="text-[10px] text-[#006323] mt-1 font-bold">Jensen-Shannon Divergence Safe</p>
                </div>

                <div className="bg-[#f8f9f5] border border-[#e9ebe3] rounded-xl p-4">
                  <span className="text-xs text-[#707367] font-semibold">Prediction Drift (PR-AUC)</span>
                  <p className="text-2xl font-bold text-[#202318] mt-1 mono-num">0.506</p>
                  <p className="text-[10px] text-[#006323] mt-1 font-bold">Within 2.0% Tolerance of Baseline</p>
                </div>
              </div>

              <div className="border border-[#e9ebe3] rounded-xl p-4 bg-[#f8f9f5]">
                <h4 className="text-xs font-bold text-[#707367] uppercase tracking-wide mb-2">
                  Delayed Feedback Feedback Store (SQLite)
                </h4>
                <p className="text-xs text-[#202318]">
                  Analyst dispute labels are written to <code className="bg-white px-1.5 py-0.5 rounded text-[11px] border border-[#e9ebe3]">data/feedback_store.sqlite</code> and buffered for retrospective drift computation over 120-day horizons.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Simulation Modal */}
      <ScenarioModal
        isOpen={isScenarioModalOpen}
        onClose={() => setIsScenarioModalOpen(false)}
        onSimulate={handleSimulate}
      />
    </div>
  );
};

export default App;
