/**
 * StrategyWorkspace — The main page. Everything visible at once.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStrategy } from '../hooks/useStrategy';
import { DataModeBanner } from '../components/DataModeBanner/DataModeBanner';
import { LegBuilder } from '../components/LegBuilder/LegBuilder';
import { PayoffChart } from '../components/PayoffChart/PayoffChart';
import { RiskScore } from '../components/MetricsPanel/RiskScore';
import { RiskMetrics } from '../components/MetricsPanel/RiskMetrics';
import { PortfolioGreeks } from '../components/MetricsPanel/PortfolioGreeks';
import { LegGreeksTable } from '../components/MetricsPanel/LegGreeksTable';
import { AssumptionDashboard } from '../components/AssumptionDashboard/AssumptionDashboard';
import { StressTestPanel } from '../components/StressTest/StressTestPanel';
import { HealthMonitor } from '../components/HealthMonitor/HealthMonitor';
import { AIPromptInput } from '../components/MetricsPanel/AIPromptInput';
import { StrategyDNA } from '../components/StrategyDNA/StrategyDNA';
import { TimeSlider } from '../components/TimeSlider/TimeSlider';
import { getTimeDecay } from '../api/client';
import { encodeStrategyToQueryString } from '../utils/strategyLink';
import type { TimeDecaySeries } from '../types/strategy';

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
    setLegs,
    saveCurrent,
    setStrategyType,
    setSymbol,
  } = useStrategy();

  const [activeTab, setActiveTab] = useState<TabKey>('payoff');
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [timeDecaySeries, setTimeDecaySeries] = useState<TimeDecaySeries | null>(null);
  const [isLoadingTimeDecay, setIsLoadingTimeDecay] = useState(false);

  useEffect(() => {
    if (autoAnalyze && state.legs.length > 0) {
      analyzeNow().then(() => {
        setIsLoadingTimeDecay(true);
        getTimeDecay(state.legs, state.strategyType, state.symbol).then(series => {
          setTimeDecaySeries(series);
          setIsLoadingTimeDecay(false);
        });
      });
      setAutoAnalyze(false);
    }
  }, [autoAnalyze, state.legs, state.symbol, state.strategyType, analyzeNow]);

  const handleSaveAndMonitor = async () => {
    await saveCurrent();
  };

  // ── COPY STRATEGY LINK ────────────────────────────────────────────────
  const handleCopyLink = async () => {
    if (state.legs.length === 0) return;
    const query = encodeStrategyToQueryString(state.legs, state.strategyType, state.symbol);
    const url = `${window.location.origin}${window.location.pathname}${query}`;
    try {
      await navigator.clipboard.writeText(url);
      // Optional: show toast here if you have a toast system
    } catch {
      // Fallback: select text for manual copy
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
    }
  };
  // ──────────────────────────────────────────────────────────────────────

  const handleSimulateAdjustment = () => {
    navigate('/adjustment', { state: { originalLegs: state.legs, symbol: state.symbol, strategyType: state.strategyType } });
  };

  const handleAnalyze = async () => {
    await analyzeNow();
    setIsLoadingTimeDecay(true);
    const series = await getTimeDecay(state.legs, state.strategyType, state.symbol);
    setTimeDecaySeries(series);
    setIsLoadingTimeDecay(false);
  };

  return (
    <div className="min-h-screen bg-background text-primary">
      <DataModeBanner dataMode={state.dataMode} />

      <div className="p-6 grid grid-cols-5 gap-6">
        {/* Left 40% */}
        <div className="col-span-2 flex flex-col gap-4">

          <AIPromptInput 
            onStrategyGenerated={(data) => {
              if (data.legs && data.legs.length > 0) {
                setLegs(data.legs);
                if (data.symbol) setSymbol(data.symbol);
                if (data.strategyName) {
                  const formattedType = data.strategyName.toLowerCase().replace(/ /g, '_') as any;
                  setStrategyType(formattedType);
                }
                setAutoAnalyze(true);
              }
            }} 
          />

          <LegBuilder
            legs={state.legs}
            strategyType={state.strategyType}
            symbol={state.symbol}
            isAnalyzing={state.isAnalyzing}
            onAddLeg={addLeg}
            onRemoveLeg={removeLeg}
            onUpdateLeg={updateLeg}
            onAnalyze={handleAnalyze}
            onStrategyTypeChange={setStrategyType}
            onSymbolChange={setSymbol}
          />

          {/* Risk Score — ALWAYS VISIBLE in left column */}
          <RiskScore metrics={state.metrics} isLoading={state.isAnalyzing} />

          {/* Strategy DNA */}
          <StrategyDNA strategyType={state.strategyType} />

          {state.error && <div className="text-loss text-sm">{state.error}</div>}

          <div className="flex gap-2">
            <button
              onClick={handleSaveAndMonitor}
              disabled={!state.metrics || state.isSaving}
              className="flex-1 border border-border rounded-control px-3 py-2 text-sm text-primary disabled:opacity-50 hover:bg-surface transition-colors"
            >
              {state.isSaving ? 'Saving…' : 'Save & Monitor'}
            </button>
            {/* ── COPY STRATEGY LINK BUTTON ───────────────────────────── */}
            <button
              onClick={handleCopyLink}
              disabled={state.legs.length === 0}
              className="flex-1 border border-border rounded-control px-3 py-2 text-sm text-primary disabled:opacity-50 hover:bg-surface transition-colors"
              title="Copy link to share this strategy"
            >
              Copy Strategy Link
            </button>
            {/* ─────────────────────────────────────────────────────────── */}
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
                <TimeSlider series={timeDecaySeries} isLoading={isLoadingTimeDecay} />
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

        {state.savedStrategyId && (
          <div className="col-span-5">
            <HealthMonitor strategyId={state.savedStrategyId} />
          </div>
        )}
      </div>
    </div>
  );
}