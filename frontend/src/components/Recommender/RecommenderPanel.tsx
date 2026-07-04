import { useState } from 'react';
import type { StrategyType } from '../../types/strategy';
import { getRecommendation, type MarketSnapshot, type RecommendationResult } from '../../utils/recommenderEngine';

interface Props {
  marketData: MarketSnapshot | null;
  onRecommend: (strategy: StrategyType, rationale: string) => void;
}

export function RecommenderPanel({ marketData, onRecommend }: Props) {
  const [selected, setSelected] = useState<'conservative' | 'moderate' | 'aggressive' | null>(null);
  const [result, setResult] = useState<RecommendationResult | null>(null);

  const profiles = [
    { id: 'conservative' as const, label: '🛡️ Conservative', desc: 'Preserve capital, stable returns' },
    { id: 'moderate' as const,      label: '⚖️ Moderate',     desc: 'Balanced growth & risk' },
    { id: 'aggressive' as const,    label: '🚀 Aggressive',   desc: 'Maximize returns, high volatility' },
  ];

  const handleClick = (profile: typeof profiles[0]) => {
    if (!marketData) return;
    setSelected(profile.id);
    const rec = getRecommendation(marketData, profile.id);
    setResult(rec);
    onRecommend(rec.primary.type, rec.rationale);
  };

  if (!marketData) {
    return (
      <div className="rounded-2xl border border-border/40 bg-surface/20 p-5 text-center text-sm text-secondary/60">
        ⏳ Run an initial analysis to unlock AI Recommendations...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3">
        {profiles.map((p) => (
          <button
            key={p.id}
            onClick={() => handleClick(p)}
            className={`flex flex-col items-center gap-1 rounded-xl border p-4 text-center transition-all duration-300 hover:scale-[1.02] ${
              selected === p.id
                ? 'border-accent bg-accent/10 ring-2 ring-accent/50'
                : 'border-border/50 hover:border-accent/30 hover:bg-surface/30'
            }`}
          >
            <span className="text-2xl">{p.label.split(' ')[0]}</span>
            <span className="text-sm font-semibold text-primary">{p.label.replace(/[^a-zA-Z ]/g, '')}</span>
            <span className="text-[10px] text-secondary/70">{p.desc}</span>
          </button>
        ))}
      </div>

      {result && (
        <div className="rounded-xl border border-accent/20 bg-surface/20 p-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-accent">⭐ Recommended</span>
            <span className="text-xs font-medium text-secondary/60">Fit Score: {result.primary.score}/100</span>
          </div>
          <p className="mt-1 text-sm font-medium text-primary">
            {result.primary.type.replace(/_/g, ' ').toUpperCase()}
          </p>
          <p className="mt-1 text-xs text-secondary/80">{result.rationale}</p>
          {result.primary.warnings.length > 0 && (
            <p className="mt-2 text-xs text-warning">⚠️ {result.primary.warnings[0]}</p>
          )}
        </div>
      )}
    </div>
  );
}