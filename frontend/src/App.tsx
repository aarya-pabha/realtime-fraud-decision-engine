import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { StatCards } from './components/StatCards';
import { AnalyticsChart } from './components/AnalyticsChart';
import { StreamFeed } from './components/StreamFeed';
import { PolicyActionBox } from './components/PolicyActionBox';
import { ProgressDonut } from './components/ProgressDonut';
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
        avgLatencyMs={kpis.avg_latency_ms}
        p95LatencyMs={kpis.p95_latency_ms}
      />

      {/* Main Content Area */}
      <main className="flex-1 ml-64 p-6 lg:p-8 max-w-[1600px]">
        <Header
          onOpenScenarioModal={() => setIsScenarioModalOpen(true)}
          onRefreshStream={fetchStreamData}
          isStreaming={streamOnline}
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
              <div className="space-y-6">
                <PolicyActionBox
                  selectedTx={selectedTx}
                  onSubmitFeedback={handleSubmitFeedback}
                />
                <ProgressDonut kpis={kpis} />
              </div>
            </div>

            {/* Historical Analytics Chart (Full Width at Bottom) */}
            <AnalyticsChart kpis={kpis} />
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
