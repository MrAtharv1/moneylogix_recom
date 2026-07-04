/**
 * StrategyDNA — Plain English explanation of what a strategy is and needs.
 * Designed for non-experts. Zero jargon without explanation.
 */
import { useEffect, useState } from 'react';
import { getStrategyDNA } from '../../api/client';
import type { StrategyDNA as StrategyDNAType, StrategyType } from '../../types/strategy';

interface Props {
  strategyType: StrategyType;
}

export function StrategyDNA({ strategyType }: Props) {
  const [dna, setDna] = useState<StrategyDNAType | null>(null);

  useEffect(() => {
    getStrategyDNA(strategyType).then(setDna);
  }, [strategyType]);

  if (!dna || strategyType === 'custom') return null;

  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-border/40 bg-surface/20 p-5 shadow-sm backdrop-blur-md">
      {/* Header */}
      <div className="flex flex-col gap-1.5">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-secondary/70">
          Strategy DNA
        </h3>
        <p className="text-[13px] font-medium leading-relaxed text-primary/90">{dna.goal}</p>
      </div>

      {/* 2x2 grid of key attributes */}
      <div className="grid grid-cols-2 gap-2.5">
        <DNACard
          icon="📈"
          label="Best Market"
          value={dna.best_market}
          valueClass="text-profit"
        />
        <DNACard
          icon="📉"
          label="Worst Market"
          value={dna.worst_market}
          valueClass="text-loss"
        />
        <DNACard
          icon="⏱"
          label="Time Sensitivity"
          value={dna.time_sensitivity}
          valueClass="text-warning"
        />
        <DNACard
          icon="〰️"
          label="Vol Sensitivity"
          value={dna.volatility_sensitivity}
          valueClass="text-accent"
        />
      </div>

      {/* Key Risks */}
      {dna.key_risks.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-[10px] font-semibold uppercase tracking-wider text-secondary/60">Key Risks</h4>
          <div className="flex flex-wrap gap-1.5">
            {dna.key_risks.map((risk, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 rounded-lg border border-loss/20 bg-loss/5 px-2 py-1 text-[11px] font-medium text-loss/90"
              >
                <span className="text-[10px]">⚠</span> {risk}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Ideal Entry Conditions */}
      {dna.ideal_entry_conditions.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-[10px] font-semibold uppercase tracking-wider text-secondary/60">
            Ideal Entry
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {dna.ideal_entry_conditions.map((cond, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 rounded-lg border border-profit/20 bg-profit/5 px-2 py-1 text-[11px] font-medium text-profit/90"
              >
                <span className="text-[10px]">✓</span> {cond}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DNACard({
  icon, label, value, valueClass
}: {
  icon: string; label: string; value: string; valueClass: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border/30 bg-surface/30 p-3 transition-colors hover:bg-surface/50">
      <div className="flex items-center gap-1.5">
        <span className="text-xs opacity-80">{icon}</span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-secondary/70">{label}</span>
      </div>
      <p className={`text-xs font-medium tracking-tight ${valueClass}`}>
        {value}
      </p>
    </div>
  );
}