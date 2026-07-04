/**
 * RiskScore — Displays the backend-computed risk score with tier badge,
 * progress bar, and 6-factor breakdown so it isn't a black box.
 */
import type { StrategyMetrics } from '../../types/strategy';

interface Props {
  metrics: StrategyMetrics | null;
  isLoading: boolean;
}

const FACTOR_LABELS: { key: string; label: string }[] = [
  { key: 'delta', label: 'Delta' },
  { key: 'gamma', label: 'Gamma' },
  { key: 'vega', label: 'Vega' },
  { key: 'margin', label: 'Margin' },
  { key: 'maxLoss', label: 'Max Loss' },
  { key: 'liquidity', label: 'Liquidity' },
];

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-border/40 bg-surface/20 p-5 shadow-sm backdrop-blur-md">
      <div className="mb-4 h-3 w-20 animate-pulse rounded bg-border/50" />
      <div className="mb-3 h-10 w-24 animate-pulse rounded bg-border/50" />
      <div className="mb-4 h-2 w-full animate-pulse rounded bg-border/50" />
      <div className="flex flex-col gap-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-2 w-full animate-pulse rounded bg-border/30" />
        ))}
      </div>
    </div>
  );
}

export function RiskScore({ metrics, isLoading }: Props) {
  if (isLoading) {
    return <SkeletonCard />;
  }

  const rs = metrics?.risk_score;

  if (!rs) {
    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 p-5 text-center shadow-sm backdrop-blur-md">
        <span className="text-sm font-medium text-secondary">Risk Analysis</span>
        <span className="mt-1 text-xs text-secondary/60">Run analysis to compute strategy risk</span>
      </div>
    );
  }

  const colorMap: Record<string, { text: string; bg: string; bar: string; border: string }> = {
    green:  { text: 'text-profit',  bg: 'bg-profit/10',  bar: 'bg-profit', border: 'border-profit/20' },
    amber:  { text: 'text-warning', bg: 'bg-warning/10', bar: 'bg-warning', border: 'border-warning/20' },
    red:    { text: 'text-loss',    bg: 'bg-loss/10',    bar: 'bg-loss', border: 'border-loss/20' },
  };

  const theme = colorMap[rs.color] ?? colorMap.amber;

  return (
    <div className={`flex flex-col rounded-2xl border ${theme.border} bg-surface/20 p-5 shadow-sm backdrop-blur-md transition-all`}>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-secondary/80">
          Risk Score
        </span>
        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${theme.bg} ${theme.text}`}>
          {rs.tier}
        </span>
      </div>
      
      <div className="mb-3 flex items-baseline gap-1.5">
        <span className={`text-4xl font-bold tabular-nums tracking-tight ${theme.text}`}>
          {rs.score}
        </span>
        <span className="text-sm font-medium text-secondary/60">/ 100</span>
      </div>

      {/* Overall score bar */}
      <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-background/50 shadow-inner">
        <div
          className={`h-full ${theme.bar} transition-all duration-1000 ease-out`}
          style={{ width: `${rs.score}%` }}
        />
      </div>

      {rs.interpretation && (
        <p className="mb-5 text-xs leading-relaxed text-secondary/80">
          {rs.interpretation}
        </p>
      )}

      {/* Per-factor breakdown */}
      <div className="flex flex-col gap-2.5 pt-1">
        {FACTOR_LABELS.map(({ key, label }) => {
          const val = rs.breakdown?.[key] ?? 0;
          return (
            <div key={key} className="group flex items-center gap-3">
              <span className="w-16 shrink-0 text-[11px] font-medium text-secondary/70 transition-colors group-hover:text-secondary">
                {label}
              </span>
              <div className="flex-1 overflow-hidden rounded-full bg-background/40 h-1">
                <div
                  className="h-full bg-secondary/40 transition-all duration-700 ease-out group-hover:bg-secondary/60"
                  style={{ width: `${val}%` }}
                />
              </div>
              <span className="w-8 shrink-0 text-right text-[11px] font-medium tabular-nums text-secondary/70 transition-colors group-hover:text-secondary">
                {val}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}