import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { StatCards } from './components/StatCards';
import { FinancialSavingsCard } from './components/FinancialSavingsCard';
import { StreamFeed } from './components/StreamFeed';
import { PolicyActionBox } from './components/PolicyActionBox';
import { ScenarioModal } from './components/ScenarioModal';
import { SimulatorView } from './components/SimulatorView';
import { DriftView } from './components/DriftView';
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
  liability_shifted_dollars: 0.0,
  friction_saved_dollars: 0.0,
  net_savings_dollars: 0.0,
  static_loss_dollars: 0.0,
  tuned_static_loss_dollars: 0.0,
  dynamic_loss_dollars: 0.0,
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
        setSelectedTx((prev) => {
          if (prev) return prev;
          return dataRecent.length > 0 ? dataRecent[0] : null;
        });
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

  // Handle stream replay
  const handleReplayStream = async () => {
    try {
      const res = await fetch('/v1/stream/replay', { method: 'POST' });
      if (res.ok) {
        setSelectedTx(null);
        await fetchStreamData();
      }
    } catch (err) {
      console.error('Replay error:', err);
    }
  };

  useEffect(() => {
    fetchStreamData();

    const interval = setInterval(() => {
      fetchStreamData();
    }, 900);

    return () => clearInterval(interval);
  }, []);

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
        TransactionAmt: 150.0,
        ProductCD: 'C',
        card1: 8821,
        card4: 'mastercard',
        card6: 'credit',
        P_emaildomain: 'mailinator.com',
        R_emaildomain: 'protonmail.com',
        C1: 15.0,
        C2: 15.0,
        tx_count_5m: 14,
        tx_count_1h: 42,
        amt_sum_24h: 5800.0,
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
        C1: 1.0,
        tx_count_5m: 1,
        tx_count_1h: 2,
        amt_sum_24h: 2400.0,
        TransactionDT: 86400,
      });
    } else if (preset === 'normal') {
      handleSimulate({
        TransactionAmt: 25.0,
        ProductCD: 'W',
        card1: 10230,
        card4: 'visa',
        card6: 'debit',
        P_emaildomain: 'gmail.com',
        C1: 1.0,
        tx_count_5m: 0,
        tx_count_1h: 1,
        amt_sum_24h: 25.0,
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
          is_fraud: isChargeback ? 1 : 0,
          is_fraud_chargeback: isChargeback ? 1 : 0,
          analyst_id: 'analyst_ops',
          dispute_amount: selectedTx?.transaction_amount || 0.0,
          chargeback_reason_code: isChargeback ? '10.4_FRAUD_CARD_ABSENT_ENVIRONMENT' : 'LEGITIMATE_PURCHASE',
        }),
      });
    } catch (err) {
      console.error('Feedback error:', err);
    }
  };

  const handleInjectDriftWave = async () => {
    try {
      const res = await fetch('/v1/stream/drift/inject', { method: 'POST' });
      if (res.ok) {
        fetchStreamData();
        window.dispatchEvent(new CustomEvent('fraud-engine:drift-updated'));
      }
    } catch (err) {
      console.error('Failed to inject drift wave:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9f5] flex text-[#202318] antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        streamOnline={streamOnline}
        avgLatencyMs={kpis.avg_latency_ms}
        p95LatencyMs={kpis.p95_latency_ms}
      />

      {/* Main Content Area */}
      <main className="flex-1 ml-64 p-6 lg:p-8 max-w-[1600px]">
        <Header
          activeTab={activeTab}
          onOpenScenarioModal={() => setIsScenarioModalOpen(true)}
          onReplayStream={handleReplayStream}
          onInjectDriftWave={handleInjectDriftWave}
        />

        {/* Tab 1: Full Tasko Dashboard View */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* 4 Stat KPI Bento Cards */}
            <StatCards kpis={kpis} />

            {/* Middle Section: 2/3 Left (Stream) vs 1/3 Right (Policy Forensics + Donut) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column (2/3 width) */}
              <div className="lg:col-span-2">
                <StreamFeed
                  transactions={transactions}
                  selectedTxId={selectedTx ? selectedTx.transaction_id : null}
                  onSelectTransaction={(tx) => setSelectedTx(tx)}
                />
              </div>

              {/* Right Column (1/3 width) */}
              <div>
                <PolicyActionBox
                  selectedTx={selectedTx}
                  onSubmitFeedback={handleSubmitFeedback}
                />
              </div>
            </div>

            {/* Financial ROI & Money Saved Card (Full Width at Bottom) */}
            <FinancialSavingsCard kpis={kpis} />
          </div>
        )}

        {/* Tab 2: Interactive 3DS Simulator View */}
        {activeTab === 'simulator' && (
          <SimulatorView
            selectedTx={selectedTx}
            onSimulatePreset={handleSimulatePreset}
            onCustomSimulate={handleSimulate}
          />
        )}

        {/* Tab 3: Evidently AI Drift Center View */}
        {activeTab === 'drift' && <DriftView />}
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
