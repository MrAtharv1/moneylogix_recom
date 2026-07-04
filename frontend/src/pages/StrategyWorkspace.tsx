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
import { encodeStrategyToQueryString } from '../utils/strategyLink';
import type { StrategyType } from '../types/strategy';

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
    triggerAutoAnalyze,
  } = useStrategy();

  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem('activeTab') as TabKey;
    return saved || 'payoff';
  });

  // ── NEW: Copy button spinner state ──
  const [isCopying, setIsCopying] = useState(false);

  useEffect(() => {
    localStorage.setItem('activeTab', activeTab);
  }, [activeTab]);

  const handleAnalyze = async () => {
    await analyzeNow();
  };

  const handleSaveAndMonitor = async () => {
    await saveCurrent();
  };

  const handleCopyLink = async () => {
    if (state.legs.length === 0) return;
    const query = encodeStrategyToQueryString(state.legs, state.strategyType, state.symbol);
    const url = `${window.location.origin}${window.location.pathname}${query}`;
    
    // ── Show spinner ──
    setIsCopying(true);

    try {
      await navigator.clipboard.writeText(url);
    } catch {
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
    }

    // ── Hide spinner after 500ms ──
    setTimeout(() => setIsCopying(false), 500);
  };

  const handleSimulateAdjustment = () => {
    navigate('/adjustment', { state: { originalLegs: state.legs, symbol: state.symbol, strategyType: state.strategyType } });
  };

  return (
    <div className="min-h-screen bg-background text-primary antialiased selection:bg-accent/20">
      <DataModeBanner dataMode={state.dataMode} />

      <main className="mx-auto grid w-full max-w-[1680px] grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-[minmax(380px,0.9fr)_minmax(0,1.4fr)] lg:px-8">
        {/* Left */}
        <section className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
          <AIPromptInput
            onStrategyGenerated={(data) => {
              if (data.legs && data.legs.length > 0) {
                setLegs(data.legs);
                if (data.symbol) setSymbol(data.symbol);
                
                // Properly scope the formatted strategy type
                const strategyTypeFormatted = (data.strategyName?.toLowerCase().replace(/ /g, '_') || 'custom') as StrategyType;
                
                if (data.strategyName) {
                  setStrategyType(strategyTypeFormatted);
                }
                
                // Trigger auto‑analysis after AI generates legs
                setTimeout(() => triggerAutoAnalyze(data.legs, strategyTypeFormatted, data.symbol), 300);
              }
            }}
          />

          {state.legs.length === 0 && !state.isAnalyzing && (
            <div className="flex items-center justify-center gap-4 py-1">
              <div className="h-px flex-1 bg-border/40" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-secondary/50">Or Build Manually</span>
              <div className="h-px flex-1 bg-border/40" />
            </div>
          )}

          <div className="rounded-2xl border border-border/40 bg-surface/20 p-5 shadow-sm backdrop-blur-md">
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
          </div>

          <RiskScore metrics={state.metrics} isLoading={state.isAnalyzing} />
          <StrategyDNA strategyType={state.strategyType} />

          {state.error && (
            <div className="rounded-lg bg-loss/10 px-4 py-3 text-sm text-loss">{state.error}</div>
          )}

          <div className="grid grid-cols-1 gap-3 rounded-2xl border border-border/40 bg-surface/20 p-2 sm:grid-cols-3">
            <button
              onClick={handleSaveAndMonitor}
              disabled={!state.metrics || state.isSaving}
              className="flex items-center justify-center rounded-xl border border-border/50 bg-surface px-3 py-2 text-xs font-medium text-primary shadow-sm transition-all hover:bg-surface/80 disabled:opacity-40"
            >
              {state.isSaving ? 'Saving…' : 'Save & Monitor'}
            </button>
            
            {/* ── Copy button with spinner ── */}
            <button
              onClick={handleCopyLink}
              disabled={state.legs.length === 0 || isCopying}
              className="flex items-center justify-center rounded-xl border border-border/50 bg-surface px-3 py-2 text-xs font-medium text-primary shadow-sm transition-all hover:bg-surface/80 disabled:opacity-40"
            >
              {isCopying ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
              ) : (
                'Copy Link'
              )}
            </button>

            <button
              onClick={handleSimulateAdjustment}
              disabled={state.legs.length === 0}
              className="flex items-center justify-center rounded-xl border border-border/50 bg-surface px-3 py-2 text-xs font-medium text-primary shadow-sm transition-all hover:bg-surface/80 disabled:opacity-40"
            >
              Adjust
            </button>
          </div>
        </section>

        {/* Right */}
        <section className="min-w-0 rounded-2xl border border-border/40 bg-surface/20 p-4 shadow-sm backdrop-blur-md sm:p-5">
          <div className="mb-5 flex items-center overflow-x-auto">
            <div className="flex w-max space-x-1 rounded-xl border border-border/40 bg-surface/30 p-1 shadow-sm">
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`rounded-lg px-5 py-1.5 text-sm font-medium transition-all ${
                    activeTab === tab.key
                      ? 'bg-surface text-primary shadow-sm'
                      : 'text-secondary hover:bg-surface/50 hover:text-primary'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="min-w-0">
            {activeTab === 'payoff' && (
              <div className="flex flex-col gap-6">
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
                
                {/* Linked to the new useStrategy state */}
                <TimeSlider series={state.timeDecaySeries} isLoading={state.isAnalyzing} />
                
                <RiskMetrics metrics={state.metrics?.risk_metrics ?? null} isLoading={state.isAnalyzing} />
              </div>
            )}

            {activeTab === 'greeks' && state.metrics && (
              <div className="flex flex-col gap-6">
                <PortfolioGreeks greeks={state.metrics.portfolio_greeks} isLoading={state.isAnalyzing} />
                <LegGreeksTable
                  legs={state.metrics.legs}
                  greeksPerLeg={state.metrics.greeks_per_leg}
                  isLoading={state.isAnalyzing}
                />
              </div>
            )}
            {activeTab === 'greeks' && !state.metrics && (
              <PortfolioGreeks greeks={null} isLoading={state.isAnalyzing} />
            )}

            {activeTab === 'assumptions' && (
              <AssumptionDashboard result={state.assumptions} isLoading={state.isAnalyzing} />
            )}

            {activeTab === 'stress' && (
              <StressTestPanel legs={state.legs} symbol={state.symbol} isVisible={activeTab === 'stress'} />
            )}
          </div>
        </section>

        {state.savedStrategyId && (
          <section className="lg:col-span-2">
            <HealthMonitor strategyId={state.savedStrategyId} />
          </section>
        )}
      </main>
    </div>
  );
}