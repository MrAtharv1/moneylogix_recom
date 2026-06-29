/**
 * StrategyWorkspace — The main page. Everything visible at once.
 *
 * Layout (desktop, 2-column):
 *
 * [DataModeBanner — full width]
 *
 * [Left 40%]                    [Right 60%]
 * Symbol + Type selector         Tab bar: Payoff | Greeks | Assumptions | Stress Test
 * LegBuilder                     Active tab content
 * [Save & Monitor button]
 *                                [HealthMonitor — hidden until saved, full width below]
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStrategy } from '../hooks/useStrategy';
import { DataModeBanner } from '../components/DataModeBanner/DataModeBanner';
import { LegBuilder } from '../components/LegBuilder/LegBuilder';
import { PayoffChart } from '../components/PayoffChart/PayoffChart';
import { RiskMetrics } from '../components/MetricsPanel/RiskMetrics';
import { PortfolioGreeks } from '../components/MetricsPanel/PortfolioGreeks';
import { LegGreeksTable } from '../components/MetricsPanel/LegGreeksTable';
import { AssumptionDashboard } from '../components/AssumptionDashboard/AssumptionDashboard';
import { StressTestPanel } from '../components/StressTest/StressTestPanel';
import { HealthMonitor } from '../components/HealthMonitor/HealthMonitor';

type TabKey = 'payoff' | 'greeks' | 'assumptions' | 'stress';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'payoff', label: 'Payoff' },
  { key: 'greeks', label: 'Greeks' },
  { key: 'assumptions', label: 'Assumptions' },
  { key: 'stress', label: 'Stress Test' },
];

export function StrategyWorkspace() {
  const navigate = useNavigate();
  const {
    state,
    addLeg,
    removeLeg,
    updateLeg,
    analyzeNow,
    saveCurrent,
    setStrategyType,
    setSymbol,
  } = useStrategy();

  const [activeTab, setActiveTab] = useState<TabKey>('payoff');

  const handleSaveAndMonitor = async () => {
    await saveCurrent();
  };

  const handleSimulateAdjustment = () => {
    navigate('/adjustment', { state: { originalLegs: state.legs, symbol: state.symbol } });
  };

  return (
    <div className="min-h-screen bg-background text-primary">
      <DataModeBanner dataMode={state.dataMode} />

      <div className="p-6 grid grid-cols-5 gap-6">
        {/* Left 40% */}
        <div className="col-span-2 flex flex-col gap-4">
          <LegBuilder
            legs={state.legs}
            strategyType={state.strategyType}
            symbol={state.symbol}
            isAnalyzing={state.isAnalyzing}
            onAddLeg={addLeg}
            onRemoveLeg={removeLeg}
            onUpdateLeg={updateLeg}
            onAnalyze={analyzeNow}
            onStrategyTypeChange={setStrategyType}
            onSymbolChange={setSymbol}
          />

          {state.error && <div className="text-loss text-sm">{state.error}</div>}

          <div className="flex gap-2">
            <button
              onClick={handleSaveAndMonitor}
              disabled={!state.metrics || state.isSaving}
              className="flex-1 border border-border rounded-control px-3 py-2 text-sm text-primary disabled:opacity-50 hover:bg-surface transition-colors"
            >
              {state.isSaving ? 'Saving…' : 'Save & Monitor'}
            </button>
            <button
              onClick={handleSimulateAdjustment}
              disabled={state.legs.length === 0}
              className="flex-1 border border-border rounded-control px-3 py-2 text-sm text-primary disabled:opacity-50 hover:bg-surface transition-colors"
            >
              Simulate Adjustment
            </button>
          </div>
        </div>

        {/* Right 60% */}
        <div className="col-span-3 flex flex-col gap-4">
          <div className="flex border-b border-border">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 text-sm transition-colors ${
                  activeTab === tab.key
                    ? 'text-accent border-b-2 border-accent'
                    : 'text-secondary hover:text-primary'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div>
            {activeTab === 'payoff' && (
              <div className="flex flex-col gap-4">
                {state.metrics ? (
                  <PayoffChart
                    curve={state.metrics.payoff_curve}
                    breakevens={state.metrics.risk_metrics.breakevens}
                    maxProfit={state.metrics.risk_metrics.max_profit}
                    maxLoss={state.metrics.risk_metrics.max_loss}
                  />
                ) : (
                  <PayoffChart curve={[]} breakevens={[]} maxProfit={0} maxLoss={0} />
                )}
                <RiskMetrics metrics={state.metrics?.risk_metrics ?? null} isLoading={state.isAnalyzing} />
              </div>
            )}

            {activeTab === 'greeks' && state.metrics && (
              <div className="flex flex-col gap-4">
                <PortfolioGreeks greeks={state.metrics.portfolio_greeks} isLoading={state.isAnalyzing} />
                <LegGreeksTable
                  legs={state.metrics.legs}
                  greeksPerLeg={state.metrics.greeks_per_leg}
                  isLoading={state.isAnalyzing}
                />
              </div>
            )}
            {activeTab === 'greeks' && !state.metrics && (
              <div className="flex flex-col gap-4">
                <PortfolioGreeks greeks={null} isLoading={state.isAnalyzing} />
              </div>
            )}

            {activeTab === 'assumptions' && (
              <AssumptionDashboard result={state.assumptions} isLoading={state.isAnalyzing} />
            )}

            {activeTab === 'stress' && (
              <StressTestPanel legs={state.legs} symbol={state.symbol} isVisible={activeTab === 'stress'} />
            )}
          </div>
        </div>

        {/* HealthMonitor — full width, below columns, only when saved */}
        {state.savedStrategyId && (
          <div className="col-span-5">
            <HealthMonitor strategyId={state.savedStrategyId} />
          </div>
        )}
      </div>
    </div>
  );
}
