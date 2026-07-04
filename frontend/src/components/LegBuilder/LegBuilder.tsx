/**
 * LegBuilder — Multi-leg strategy construction panel.
 * Shows list of legs, add/analyze buttons, strategy type selector.
 */
import { AnimatePresence } from 'framer-motion';
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
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-secondary/80">
            Symbol
          </label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => onSymbolChange(e.target.value.toUpperCase())}
            className="h-10 w-full rounded-xl ring-1 ring-white/5 bg-surface/30 px-3 text-sm font-medium text-primary shadow-sm transition-colors focus:bg-surface focus:outline-none focus:ring-2 focus:ring-accent/50"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-secondary/80">
            Strategy Type
          </label>
          <select
            value={strategyType}
            onChange={(e) => onStrategyTypeChange(e.target.value as StrategyType)}
            className="h-10 w-full appearance-none rounded-xl ring-1 ring-white/5 bg-surface/30 px-3 text-sm text-primary shadow-sm transition-colors focus:bg-surface focus:outline-none focus:ring-2 focus:ring-accent/50"
          >
            {Object.entries(STRATEGY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-2.5 overflow-hidden">
        {legs.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 bg-surface/20 py-10 text-center text-sm text-secondary/70">
            <span>No legs configured.</span>
            <span className="mt-1 text-xs text-secondary/50">Add a leg to begin modeling your strategy.</span>
          </div>
        )}
        
        {/* FRAMER MOTION WRAPPER */}
        <AnimatePresence mode="popLayout">
          {legs.map((leg, index) => (
            <LegRow
              key={leg.id}
              leg={leg}
              index={index}
              onUpdate={(updates) => onUpdateLeg(leg.id, updates)}
              onDelete={() => onRemoveLeg(leg.id)}
            />
          ))}
        </AnimatePresence>
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <button
          onClick={() => onAddLeg()}
          className="flex h-10 items-center justify-center rounded-xl border border-dashed border-border/60 bg-transparent text-sm font-medium text-secondary transition-all hover:border-border hover:bg-surface/40 hover:text-primary focus:outline-none focus:ring-2 focus:ring-accent/20"
        >
          + Add Leg
        </button>
        <button
          onClick={onAnalyze}
          disabled={legs.length === 0 || isAnalyzing}
          className="flex h-10 items-center justify-center rounded-xl bg-accent text-sm font-medium text-white shadow-sm transition-all hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:ring-offset-2 focus:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isAnalyzing ? 'Analyzing…' : 'Analyze Strategy'}
        </button>
      </div>
    </div>
  );
}