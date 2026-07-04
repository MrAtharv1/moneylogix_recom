import { useState, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import type { Leg, AdjustmentSimulateResponse, StrategyType } from '../types/strategy';
import { simulateAdjustment } from '../api/client';
import { LegBuilder } from '../components/LegBuilder/LegBuilder';
import { PayoffChart } from '../components/PayoffChart/PayoffChart';
import { RiskMetrics } from '../components/MetricsPanel/RiskMetrics';
import { RiskScore } from '../components/MetricsPanel/RiskScore';
import { getPnLClass } from '../utils/formatters';

interface LocationState {
  originalLegs?: Leg[];
  symbol?: string;
  strategyType?: StrategyType | string;
}

export function AdjustmentView() {
  const navigate = useNavigate();
  const location = useLocation();
  const { originalLegs = [], symbol = 'NIFTY', strategyType = 'custom' } = (location.state as LocationState) || {};

  if (!originalLegs.length) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-primary">
        <div className="flex max-w-md flex-col items-center gap-4 rounded-2xl border border-border/40 bg-surface/20 p-8 text-center">
          <div className="text-sm font-medium text-loss">No strategy data found.</div>
          <p className="text-xs text-secondary">Build a strategy first.</p>
          <button onClick={() => navigate('/')} className="mt-2 rounded-xl bg-surface px-4 py-2 text-sm font-medium">
            Go to Workspace
          </button>
        </div>
      </div>
    );
  }

  const [adjustedLegs, setAdjustedLegs] = useState<Leg[]>(() => originalLegs.map((leg) => ({ ...leg })));
  const [comparison, setComparison] = useState<AdjustmentSimulateResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ensure strategyType is valid
  const validStrategyType: StrategyType = (strategyType as StrategyType) || 'custom';

  const xAxisRange = useMemo((): [number, number] | undefined => {
    const curve = comparison?.original.payoff_curve;
    if (!curve || curve.length === 0) return undefined;
    const prices = curve.map((p) => p.price);
    const mid = prices[Math.floor(prices.length / 2)];
    return [mid * 0.9, mid * 1.1];
  }, [comparison]);

  const addLeg = (overrides: Partial<Leg> = {}) => {
    const base = originalLegs[0] || {};
    setAdjustedLegs((prev) => [
      ...prev,
      {
        id: uuidv4(),
        symbol,
        strike: base.strike || 19000,
        expiry: base.expiry || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        option_type: 'call',
        side: 'buy',
        quantity: base.quantity || 1,
        lot_size: base.lot_size || 50,
        iv: base.iv || 0.138,
        ...overrides,
      },
    ]);
  };

  const removeLeg = (id: string) => setAdjustedLegs((prev) => prev.filter((leg) => leg.id !== id));
  const updateLeg = (id: string, updates: Partial<Leg>) =>
    setAdjustedLegs((prev) => prev.map((leg) => (leg.id === id ? { ...leg, ...updates } : leg)));

  const handleCompare = async () => {
    setIsComparing(true);
    setError(null);
    try {
      const result = await simulateAdjustment(originalLegs, adjustedLegs, symbol);
      if (result) {
        setComparison(result);
      } else {
        setError('Comparison failed.');
      }
    } catch (e: any) {
      setError(e?.message || 'Network error.');
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background px-4 py-6 text-primary antialiased selection:bg-accent/20 lg:px-8">
      <div className="mx-auto max-w-[1680px]">
        <header className="mb-6 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex h-9 items-center justify-center rounded-xl border border-border/40 bg-surface/20 px-4 text-sm font-medium text-secondary shadow-sm backdrop-blur-md transition-all hover:bg-surface/40 hover:text-primary"
          >
            ← Back to Workspace
          </button>
          <h1 className="text-xl font-semibold tracking-tight text-primary">Simulate Adjustment</h1>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left: Current */}
          <section className="flex flex-col gap-5 rounded-2xl border border-border/20 bg-surface/5 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Current Baseline</h2>
              <span className="rounded-md bg-surface/30 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-secondary/60">
                Read Only
              </span>
            </div>
            <div className="flex flex-col gap-2">
              {originalLegs.map((leg, i) => (
                <div key={leg.id} className="flex items-center gap-3 rounded-xl border border-border/30 bg-surface/10 px-4 py-3 opacity-80 shadow-sm transition-opacity hover:opacity-100">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-background/50 text-[11px] font-medium text-secondary/70 shadow-inner">
                    {i + 1}
                  </span>
                  <div className="flex flex-1 items-center justify-between text-sm">
                    <span className="font-medium tabular-nums text-primary">
                      {leg.strike} <span className="uppercase text-secondary">{leg.option_type}</span>
                    </span>
                    <span
                      className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
                        leg.side === 'buy' ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'
                      }`}
                    >
                      {leg.side}
                    </span>
                    <span className="text-[11px] text-secondary">
                      Qty: <span className="font-medium tabular-nums text-primary">{leg.quantity}</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
            {comparison && (
              <div className="mt-2 flex flex-col gap-5 opacity-90">
                <RiskScore metrics={comparison.original} isLoading={false} />
                <RiskMetrics metrics={comparison.original.risk_metrics} isLoading={false} />
              </div>
            )}
          </section>

          {/* Right: Adjusted */}
          <section className="flex flex-col gap-5 rounded-2xl border border-accent/20 bg-surface/20 p-5 shadow-[0_0_40px_-15px_rgba(79,140,255,0.05)] backdrop-blur-md">
            <div className="flex items-center justify-between">
              <h2 className="text-[11px] font-semibold uppercase tracking-wider text-accent/80">Adjusted Strategy</h2>
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent"></span>
              </span>
            </div>
            <LegBuilder
              legs={adjustedLegs}
              strategyType={validStrategyType}
              symbol={symbol}
              isAnalyzing={isComparing}
              onAddLeg={addLeg}
              onRemoveLeg={removeLeg}
              onUpdateLeg={updateLeg}
              onAnalyze={handleCompare}
              onStrategyTypeChange={() => {}}
              onSymbolChange={() => {}}
            />
            {comparison && (
              <div className="mt-2">
                <RiskScore metrics={comparison.adjusted} isLoading={false} />
              </div>
            )}
          </section>
        </div>

        <div className="mt-8 flex flex-col items-center justify-center gap-3">
          <button
            onClick={handleCompare}
            disabled={isComparing}
            className="flex h-12 w-full max-w-sm items-center justify-center rounded-xl bg-accent px-8 text-sm font-semibold text-white shadow-sm transition-all hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:ring-offset-2 focus:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isComparing ? 'Simulating Adjustment...' : 'Compare Strategies'}
          </button>
          {error && <span className="rounded-lg bg-loss/10 px-4 py-2 text-sm text-loss">{error}</span>}
        </div>

        {comparison && (
          <div className="mt-10 flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex w-full flex-col overflow-hidden rounded-2xl border border-border/40 bg-surface/20 shadow-sm backdrop-blur-md sm:flex-row">
              <div className="flex flex-1 flex-col justify-center border-r border-border/30 p-5 transition-colors hover:bg-surface/30 sm:last:border-r-0">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Max Profit Change</div>
                <div className={`text-xl font-semibold tabular-nums tracking-tight ${getPnLClass(comparison.comparison.delta_max_profit)}`}>
                  {comparison.comparison.max_profit_changed_by}
                </div>
              </div>
              <div className="flex flex-1 flex-col justify-center border-r border-border/30 p-5 transition-colors hover:bg-surface/30 sm:last:border-r-0">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Max Loss Change</div>
                <div className={`text-xl font-semibold tabular-nums tracking-tight ${getPnLClass(comparison.comparison.delta_max_loss)}`}>
                  {comparison.comparison.max_loss_changed_by}
                </div>
              </div>
              <div className="flex flex-1 flex-col justify-center border-r border-border/30 p-5 transition-colors hover:bg-surface/30 sm:last:border-r-0">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Margin Change</div>
                <div className="text-xl font-semibold tabular-nums tracking-tight text-primary">
                  {comparison.comparison.margin_changed_by}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-border/40 bg-surface/30 p-5 shadow-sm">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Analysis Summary</div>
              <p className="text-sm leading-relaxed text-primary/90">{comparison.comparison.summary}</p>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="flex flex-col gap-4 rounded-2xl border border-border/40 bg-surface/10 p-5 shadow-sm backdrop-blur-md">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Baseline Payoff</h3>
                <PayoffChart
                  curve={comparison.original.payoff_curve}
                  breakevens={comparison.original.risk_metrics.breakevens}
                  maxProfit={comparison.original.risk_metrics.max_profit}
                  maxLoss={comparison.original.risk_metrics.max_loss}
                  xAxisRange={xAxisRange}
                />
              </div>
              <div className="flex flex-col gap-4 rounded-2xl border border-accent/10 bg-surface/20 p-5 shadow-sm backdrop-blur-md">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-accent/80">Adjusted Payoff</h3>
                <PayoffChart
                  curve={comparison.adjusted.payoff_curve}
                  breakevens={comparison.adjusted.risk_metrics.breakevens}
                  maxProfit={comparison.adjusted.risk_metrics.max_profit}
                  maxLoss={comparison.adjusted.risk_metrics.max_loss}
                  xAxisRange={xAxisRange}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}