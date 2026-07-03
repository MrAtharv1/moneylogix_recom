/**
 * RiskMetrics — Max Profit, Max Loss, Breakeven(s), Probability of Profit, Margin Required
 * Layout: 2-column grid of stat cards
 */
import type { RiskMetrics as RiskMetricsType } from '../../types/strategy';
import { formatINR, formatPct, formatPrice } from '../../utils/formatters';

interface Props {
  metrics: RiskMetricsType | null;
  isLoading: boolean;
}

function StatCard({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="bg-surface border border-border rounded-card p-3">
      <div className="text-secondary text-xs mb-1">{label}</div>
      <div className={`text-lg font-semibold ${valueClass ?? 'text-primary'}`}>{value}</div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-surface border border-border rounded-card p-3">
      <div className="skeleton h-3 w-20 mb-2" />
      <div className="skeleton h-5 w-24" />
    </div>
  );
}

export function RiskMetrics({ metrics, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (!metrics) {
    return <div className="text-secondary text-sm p-4">Run analysis to see risk metrics</div>;
  }

  const maxProfitUnlimited = metrics.max_profit >= 999999999;
  const maxLossUnlimited = metrics.max_loss <= -999999999;

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        label="Max Profit"
        value={maxProfitUnlimited ? 'Unlimited' : formatINR(metrics.max_profit)}
        valueClass="text-profit"
      />
      <StatCard
        label="Max Loss"
        value={maxLossUnlimited ? 'Unlimited Loss' : formatINR(metrics.max_loss)}
        valueClass="text-loss"
      />
      <StatCard
        label="Breakeven(s)"
        value={
          metrics.breakevens.length > 0
            ? metrics.breakevens.map((b) => formatPrice(b)).join(', ')
            : '—'
        }
      />
      <StatCard label="Probability of Profit" value={formatPct(metrics.probability_of_profit)} />
      <StatCard label="Margin Required" value={formatINR(metrics.margin_required)} />
    </div>
  );
}