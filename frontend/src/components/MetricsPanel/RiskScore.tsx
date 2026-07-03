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
    <div className="bg-surface border border-border rounded-card p-4">
      <div className="skeleton h-3 w-20 mb-3" />
      <div className="skeleton h-8 w-24 mb-2" />
      <div className="skeleton h-3 w-28" />
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
      <div className="bg-surface border border-border rounded-card p-4">
        <div className="text-secondary text-xs mb-1">Risk Score</div>
        <div className="text-secondary text-sm">Run analysis to see your risk score</div>
      </div>
    );
  }

  const colorMap: Record<string, { text: string; bg: string; bar: string }> = {
    green:  { text: 'text-profit',  bg: 'bg-profit/10',  bar: 'bg-profit' },
    amber:  { text: 'text-warning', bg: 'bg-warning/10', bar: 'bg-warning' },
    red:    { text: 'text-loss',    bg: 'bg-loss/10',    bar: 'bg-loss' },
  };

  const theme = colorMap[rs.color] ?? colorMap.amber;

  return (
    <div className={`border border-border rounded-card p-4 ${theme.bg}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-secondary text-xs">Risk Score</span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${theme.bg} ${theme.text}`}>
          {rs.tier}
        </span>
      </div>
      <div className="flex items-baseline gap-2 mb-1">
        <span className={`text-3xl font-bold ${theme.text}`}>{rs.score}</span>
        <span className="text-secondary text-sm">/ 100</span>
      </div>

      {/* Overall score bar */}
      <div className="w-full h-2 rounded-full bg-background overflow-hidden mb-3">
        <div
          className={`h-full ${theme.bar} transition-all duration-700`}
          style={{ width: `${rs.score}%` }}
        />
      </div>

      {rs.interpretation && (
        <p className="text-secondary text-xs leading-relaxed mb-3">
          {rs.interpretation}
        </p>
      )}

      {/* Per-factor breakdown so the score isn't a black box */}
      <div className="flex flex-col gap-1.5">
        {FACTOR_LABELS.map(({ key, label }) => {
          const val = rs.breakdown?.[key] ?? 0;
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="text-secondary text-xs w-14 shrink-0">{label}</span>
              <div className="flex-1 h-1.5 rounded-full bg-background overflow-hidden">
                <div
                  className="h-full bg-secondary/60"
                  style={{ width: `${val}%` }}
                />
              </div>
              <span className="text-secondary text-xs w-8 text-right shrink-0">
                {val}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}