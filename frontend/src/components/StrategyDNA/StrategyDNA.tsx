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
    <div className="rounded-xl border border-[#2d3148] bg-[#1a1d27] p-5 space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold text-[#94a3b8] uppercase tracking-wider mb-1">
          Strategy DNA
        </h3>
        <p className="text-[#e2e8f0] text-base font-medium">{dna.goal}</p>
      </div>

      {/* 2x2 grid of key attributes */}
      <div className="grid grid-cols-2 gap-3">
        <DNACard
          icon="📈"
          label="Best Market"
          value={dna.best_market}
          valueColor="#22c55e"
        />
        <DNACard
          icon="📉"
          label="Worst Market"
          value={dna.worst_market}
          valueColor="#ef4444"
        />
        <DNACard
          icon="⏱"
          label="Time Sensitivity"
          value={dna.time_sensitivity}
          valueColor="#f59e0b"
        />
        <DNACard
          icon="〰️"
          label="Volatility Sensitivity"
          value={dna.volatility_sensitivity}
          valueColor="#3b82f6"
        />
      </div>

      {/* Key Risks */}
      <div>
        <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-2">Key Risks</p>
        <div className="flex flex-wrap gap-2">
          {dna.key_risks.map((risk, i) => (
            <span
              key={i}
              className="text-xs px-2 py-1 rounded-md border"
              style={{
                color: '#ef4444',
                borderColor: 'rgba(239,68,68,0.3)',
                background: 'rgba(239,68,68,0.05)'
              }}
            >
              ⚠ {risk}
            </span>
          ))}
        </div>
      </div>

      {/* Ideal Entry Conditions */}
      <div>
        <p className="text-xs text-[#94a3b8] uppercase tracking-wider mb-2">
          Ideal Entry Conditions
        </p>
        <div className="flex flex-wrap gap-2">
          {dna.ideal_entry_conditions.map((cond, i) => (
            <span
              key={i}
              className="text-xs px-2 py-1 rounded-md border"
              style={{
                color: '#22c55e',
                borderColor: 'rgba(34,197,94,0.3)',
                background: 'rgba(34,197,94,0.05)'
              }}
            >
              ✓ {cond}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function DNACard({
  icon, label, value, valueColor
}: {
  icon: string; label: string; value: string; valueColor: string;
}) {
  return (
    <div className="rounded-lg bg-[#0f1117] border border-[#2d3148] p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-sm">{icon}</span>
        <span className="text-xs text-[#94a3b8]">{label}</span>
      </div>
      <p className="text-xs font-medium" style={{ color: valueColor }}>
        {value}
      </p>
    </div>
  );
}