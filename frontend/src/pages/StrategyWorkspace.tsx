import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import { useStrategy } from '../hooks/useStrategy';
import { useOptionChain } from '../hooks/useOptionChain';
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
import { RecommenderPanel } from '../components/Recommender/RecommenderPanel';
import { StrikeLadder } from '../components/StrikeLadder/StrikeLadder';
import { buildTemplateLegs } from '../utils/templateBuilder';
import { getTimeDecay } from '../api/client';
import { encodeStrategyToQueryString } from '../utils/strategyLink';
import type { StrategyType, Leg, TimeDecaySeries } from '../types/strategy';

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

  // ─── FIX 1: Get isLoading from useOptionChain ─────────────────────────────
  const { chain, isLoading: isChainLoading } = useOptionChain(state.symbol);
  
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    const saved = localStorage.getItem('activeTab') as TabKey;
    return saved || 'payoff';
  });

  const [timeDecaySeries, setTimeDecaySeries] = useState<TimeDecaySeries | null>(null);
  const [isLoadingTimeDecay, setIsLoadingTimeDecay] = useState(false);
  
  // ─── FIX 2: State for the visual copy buffer ──────────────────────────────
  const [isCopying, setIsCopying] = useState(false);

  // ─── FIX 3: Template loading states ────────────────────────────────────────
  const [isTemplateLoading, setIsTemplateLoading] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem('activeTab', activeTab);
  }, [activeTab]);

  const handleAnalyze = async () => {
    await analyzeNow();
    setIsLoadingTimeDecay(true);
    const series = await getTimeDecay(state.legs, state.strategyType, state.symbol);
    setTimeDecaySeries(series);
    setIsLoadingTimeDecay(false);
  };

  const handleSaveAndMonitor = async () => {
    await saveCurrent();
  };

  // ─── FIX 4: Copy link with 500ms buffer ──────────────────────────────────
  const handleCopyLink = async () => {
    if (state.legs.length === 0) return;
    
    setIsCopying(true);
    
    const query = encodeStrategyToQueryString(state.legs, state.strategyType, state.symbol);
    const url = `${window.location.origin}${window.location.pathname}${query}`;
    
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

    setTimeout(() => {
      setIsCopying(false);
    }, 500);
  };

  const handleSimulateAdjustment = () => {
    navigate('/adjustment', { state: { originalLegs: state.legs, symbol: state.symbol, strategyType: state.strategyType } });
  };

  // ─── FIX 5: applyTemplateAndAnalyze with loading state ────────────────────
  const applyTemplateAndAnalyze = (strategy: StrategyType) => {
    setStrategyType(strategy);
    setTemplateError(null);

    // If chain isn't loaded yet, show loading spinner and wait
    if (!chain) {
      setIsTemplateLoading(true);
      return; // The useEffect below will apply when chain loads
    }

    if (!chain.strikes || chain.strikes.length === 0) {
      setTemplateError('❌ Option chain is empty. Please refresh or check backend.');
      return;
    }

    // Chain is ready – build the legs
    _buildAndApplyTemplate(strategy);
  };

  // ─── FIX 6: Helper to actually build and apply the template ──────────────
  const _buildAndApplyTemplate = (strategy: StrategyType) => {
    if (!chain || !chain.strikes || chain.strikes.length === 0) {
      setTemplateError('❌ Option chain is not available.');
      return;
    }

    const strikes = chain.strikes.map((s: any) => s.strike);
    const newLegs = buildTemplateLegs(
      strategy,
      chain.spot,
      strikes,
      chain.lot_size || 50,
      new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      1
    ) as Leg[];

    if (newLegs.length === 0) {
      setTemplateError('❌ Template could not be built. Try again.');
      return;
    }

    setLegs(newLegs);
    setTemplateError(null);
    triggerAutoAnalyze(newLegs, strategy, state.symbol);
  };

  // ─── FIX 7: Effect to apply pending template when chain loads ─────────────
  useEffect(() => {
    if (isTemplateLoading && chain && chain.strikes && chain.strikes.length > 0) {
      setIsTemplateLoading(false);
      const currentStrategy = state.strategyType;
      _buildAndApplyTemplate(currentStrategy);
    }
  }, [chain, isTemplateLoading, state.strategyType]);

  const handleRecommend = (strategy: StrategyType) => applyTemplateAndAnalyze(strategy);
  const handleLoadTemplate = (strategy: StrategyType) => applyTemplateAndAnalyze(strategy);

  const handleStrikeSelect = (strike: number, optionType: 'call' | 'put') => {
    const newLeg: Leg = {
      id: uuidv4(),
      symbol: state.symbol,
      strike,
      expiry: new Date(Date.now() + 30*24*60*60*1000).toISOString().split('T')[0],
      option_type: optionType,
      side: 'buy',
      quantity: 1,
      lot_size: chain?.lot_size || 50,
      iv: 0.138,
    };
    
    const newLegs = [...state.legs, newLeg];
    addLeg(newLeg);
    triggerAutoAnalyze(newLegs, state.strategyType, state.symbol);
  };

  // ─── Check if loading state for template dropdown ─────────────────────────
  const isLegBuilderLoading = isChainLoading || isTemplateLoading;

  return (
    <div className="min-h-screen bg-background text-primary antialiased selection:bg-accent/20">
      <DataModeBanner dataMode={state.dataMode} />

      <main className="mx-auto grid w-full max-w-[1680px] grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-[minmax(380px,0.9fr)_minmax(0,1.4fr)] lg:px-8">
        {/* Left */}
        <section className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
          
          <RecommenderPanel
            marketData={state.metrics && chain ? {
              ivRank: state.metrics.iv_rank,
              daysToExpiry: chain.days_to_expiry || 30,
              expectedMovePct: state.metrics.expected_move_pct,
              spot: chain.spot || 19000,
            } : null}
            onRecommend={handleRecommend}
          />

          <AIPromptInput
            onStrategyGenerated={(data) => {
              if (data.legs && data.legs.length > 0) {
                setLegs(data.legs);
                if (data.symbol) setSymbol(data.symbol);
                const strategyTypeFormatted = (data.strategyName?.toLowerCase().replace(/ /g, '_') || 'custom') as StrategyType;
                if (data.strategyName) {
                  setStrategyType(strategyTypeFormatted);
                }
                triggerAutoAnalyze(data.legs, strategyTypeFormatted, data.symbol);
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
              isChainLoading={isLegBuilderLoading}      // <── NEW
              templateError={templateError}             // <── NEW
              onAddLeg={addLeg}
              onRemoveLeg={removeLeg}
              onUpdateLeg={updateLeg}
              onSetLegs={setLegs}
              onAnalyze={handleAnalyze}
              onStrategyTypeChange={setStrategyType}
              onSymbolChange={setSymbol}
              onLoadTemplate={handleLoadTemplate}
            />
          </div>

          <StrikeLadder symbol={state.symbol} onStrikeSelect={handleStrikeSelect} />

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
            <button
              onClick={handleCopyLink}
              disabled={state.legs.length === 0 || isCopying}
              className="flex items-center justify-center rounded-xl border border-border/50 bg-surface px-3 py-2 text-xs font-medium text-primary shadow-sm transition-all hover:bg-surface/80 disabled:opacity-40"
            >
              {isCopying ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary"></span>
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
                
                <TimeSlider series={timeDecaySeries} isLoading={isLoadingTimeDecay} />
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