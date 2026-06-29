/**
 * LegBuilder — Multi-leg strategy construction panel.
 * Shows list of legs, add/analyze buttons, strategy type selector.
 */
import type { Leg, StrategyType } from '../../types/strategy';
import { LegRow } from './LegRow';

interface Props {
  legs: Leg[];
  strategyType: StrategyType;
  symbol: string;
  isAnalyzing: boolean;
  onAddLeg: () => void;
  onRemoveLeg: (id: string) => void;
  onUpdateLeg: (id: string, updates: Partial<Leg>) => void;
  onAnalyze: () => void;
  onStrategyTypeChange: (t: StrategyType) => void;
  onSymbolChange: (s: string) => void;
}

// Strategy type display names for dropdown
const STRATEGY_LABELS: Record<StrategyType, string> = {
  iron_condor: 'Iron Condor',
  long_straddle: 'Long Straddle',
  long_strangle: 'Long Strangle',
  bull_call_spread: 'Bull Call Spread',
  bull_put_spread: 'Bull Put Spread',
  bear_put_spread: 'Bear Put Spread',
  covered_call: 'Covered Call',
  custom: 'Custom Strategy',
};

export function LegBuilder({
  legs,
  strategyType,
  symbol,
  isAnalyzing,
  onAddLeg,
  onRemoveLeg,
  onUpdateLeg,
  onAnalyze,
  onStrategyTypeChange,
  onSymbolChange,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="text-secondary text-xs block mb-1">Symbol</label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => onSymbolChange(e.target.value.toUpperCase())}
            className="bg-surface border border-border rounded-control px-3 py-2 text-sm text-primary w-full"
          />
        </div>
        <div className="flex-1">
          <label className="text-secondary text-xs block mb-1">Strategy Type</label>
          <select
            value={strategyType}
            onChange={(e) => onStrategyTypeChange(e.target.value as StrategyType)}
            className="bg-surface border border-border rounded-control px-3 py-2 text-sm text-primary w-full"
          >
            {Object.entries(STRATEGY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {legs.length === 0 && (
          <div className="text-secondary text-sm p-4 border border-dashed border-border rounded-card text-center">
            No legs yet. Add a leg to start building your strategy.
          </div>
        )}
        {legs.map((leg, index) => (
          <LegRow
            key={leg.id}
            leg={leg}
            index={index}
            onUpdate={(updates) => onUpdateLeg(leg.id, updates)}
            onDelete={() => onRemoveLeg(leg.id)}
          />
        ))}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onAddLeg()}
          className="flex-1 border border-border rounded-control px-3 py-2 text-sm text-primary hover:bg-surface transition-colors"
        >
          + Add Leg
        </button>
        <button
          onClick={onAnalyze}
          disabled={legs.length === 0 || isAnalyzing}
          className="flex-1 bg-accent rounded-control px-3 py-2 text-sm text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent/90 transition-colors"
        >
          {isAnalyzing ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
    </div>
  );
}
