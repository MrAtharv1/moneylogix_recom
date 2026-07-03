/**
 * AdjustmentView — Side-by-side strategy comparison page.
 * Navigate here from StrategyWorkspace via "Simulate Adjustment" button.
 * State passed via React Router state: original legs + symbol + strategyType.
 */
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
  
  // 1. Unpack with your dynamic strategyType
  const { 
    originalLegs = [], 
    symbol = 'NIFTY', 
    strategyType = 'custom' 
  } = (location.state as LocationState) || {};

  // 2. Your Guard: if user navigates directly without state
  if (!originalLegs.length) {
    return (
      <div className="min-h-screen bg-background text-primary p-6">
        <button
          onClick={() => navigate('/')}
          className="text-secondary text-sm mb-4 hover:text-primary transition-colors"
        >
          ← Back
        </button>
        <div className="text-loss">No strategy data. Build a strategy first.</div>
      </div>
    );
  }

  const [adjustedLegs, setAdjustedLegs] = useState<Leg[]>(() => originalLegs.map((leg) => ({ ...leg })));
  const [comparison, setComparison] = useState<AdjustmentSimulateResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // CRITICAL: both payoff charts must share the same x-axis domain
  const xAxisRange = useMemo((): [number, number] | undefined => {
    const curve = comparison?.original.payoff_curve;
    if (!curve || curve.length === 0) return undefined;
    const prices = curve.map((p) => p.price);
    const originalSpot = prices[Math.floor(prices.length / 2)];
    return [originalSpot * 0.9, originalSpot * 1.1];
  }, [comparison]);

  const addLeg = (overrides: Partial<Leg> = {}) => {
    // 3. Your Smart Defaults: Use the first leg's data so we don't break asset sizes
    const baseLeg = originalLegs[0] || {};
    
    setAdjustedLegs((prev) => [
      ...prev,
      {
        id: uuidv4(),
        symbol,
        strike: baseLeg.strike || 19000,
        expiry: baseLeg.expiry || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        option_type: 'call',
        side: 'buy',
        quantity: baseLeg.quantity || 1,
        lot_size: baseLeg.lot_size || 50,
        iv: baseLeg.iv || 0.138,
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
        setError('Comparison failed. Make sure backend is running.');
      }
    } catch (e: any) {
      setError(e?.message || 'Network error during comparison.');
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-primary p-6">
      <button
        onClick={() => navigate(-1)}
        className="text-secondary text-sm mb-4 hover:text-primary transition-colors"
      >
        ← Back
      </button>

      <div className="grid grid-cols-2 gap-6">
        {/* CURRENT STRATEGY */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Current Strategy</h2>
          <div className="flex flex-col gap-2 mb-4">
            {originalLegs.map((leg, i) => (
              <div key={leg.id} className="border border-border rounded-card p-3 bg-surface text-sm">
                <span className="text-secondary mr-2">{i + 1}</span>
                {leg.strike} {leg.option_type.toUpperCase()} · {leg.side} · qty {leg.quantity}
              </div>
            ))}
          </div>
          
          {/* 4. BUGFIX APPLIED: Full object to RiskScore, slice to RiskMetrics */}
          {comparison && <RiskScore metrics={comparison.original} isLoading={false} />}
          {comparison && <RiskMetrics metrics={comparison.original.risk_metrics} isLoading={false} />}
        </div>

        {/* ADJUSTED STRATEGY */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Adjusted Strategy</h2>
          <LegBuilder
            legs={adjustedLegs}
            strategyType={strategyType as any}
            symbol={symbol}
            isAnalyzing={isComparing}
            onAddLeg={addLeg}
            onRemoveLeg={removeLeg}
            onUpdateLeg={updateLeg}
            onAnalyze={handleCompare}
            onStrategyTypeChange={() => {}}
            onSymbolChange={() => {}}
          />
          
          {/* Friend's UI addition: RiskScore for the adjusted side */}
          {comparison && <RiskScore metrics={comparison.adjusted} isLoading={false} />}
        </div>
      </div>

      <div className="mt-4">
        <button
          onClick={handleCompare}
          disabled={isComparing}
          className="bg-accent rounded-control px-4 py-2 text-sm text-white font-medium disabled:opacity-50 hover:bg-accent/90 transition-colors"
        >
          {isComparing ? 'Comparing…' : 'Compare'}
        </button>
        {error && <span className="text-loss text-sm ml-3">{error}</span>}
      </div>

      {/* COMPARISON RESULTS */}
      {comparison && (
        <div className="mt-6">
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-surface border border-border rounded-card p-3">
              <div className="text-secondary text-xs mb-1">Max Profit Change</div>
              <div className={`text-lg font-semibold ${getPnLClass(comparison.comparison.delta_max_profit)}`}>
                {comparison.comparison.max_profit_changed_by}
              </div>
            </div>
            <div className="bg-surface border border-border rounded-card p-3">
              <div className="text-secondary text-xs mb-1">Max Loss Change</div>
              <div className={`text-lg font-semibold ${getPnLClass(comparison.comparison.delta_max_loss)}`}>
                {comparison.comparison.max_loss_changed_by}
              </div>
            </div>
            <div className="bg-surface border border-border rounded-card p-3">
              <div className="text-secondary text-xs mb-1">Margin Change</div>
              <div className="text-lg font-semibold text-primary">
                {comparison.comparison.margin_changed_by}
              </div>
            </div>
          </div>

          <p className="text-secondary text-sm mb-4">{comparison.comparison.summary}</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm text-secondary mb-2">Current Payoff</h3>
              <PayoffChart
                curve={comparison.original.payoff_curve}
                breakevens={comparison.original.risk_metrics.breakevens}
                maxProfit={comparison.original.risk_metrics.max_profit}
                maxLoss={comparison.original.risk_metrics.max_loss}
                xAxisRange={xAxisRange}
              />
            </div>
            <div>
              <h3 className="text-sm text-secondary mb-2">Adjusted Payoff</h3>
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
  );
}