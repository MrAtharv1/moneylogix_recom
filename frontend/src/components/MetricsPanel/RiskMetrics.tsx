/**
 * RiskMetrics — Max Profit, Max Loss, Breakeven(s), Probability of Profit, Margin Required
 * Layout: Unified grid panel to reduce card visual noise
 */
import type { RiskMetrics as RiskMetricsType } from '../../types/strategy';
import { formatINR, formatPct, formatPrice } from '../../utils/formatters';

interface Props {
  metrics: RiskMetricsType | null;
  isLoading: boolean;
}

function StatItem({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex flex-col justify-center rounded-xl p-3 transition-colors hover:bg-surface/30">
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">{label}</div>
      <div className={`text-base font-semibold tabular-nums tracking-tight ${valueClass ?? 'text-primary'}`}>
        {value}
      </div>
    </div>
  );
}

function SkeletonItem() {
  return (
    <div className="p-3">
      <div className="mb-2 h-2.5 w-16 animate-pulse rounded bg-border/50" />
      <div className="h-5 w-24 animate-pulse rounded bg-border/50" />
    </div>
  );
}

export function RiskMetrics({ metrics, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-1 rounded-2xl border border-border/40 bg-surface/20 p-2 shadow-sm sm:grid-cols-3 md:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonItem key={i} />
        ))}
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex h-24 items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Run analysis to view risk metrics
      </div>
    );
  }

  const maxProfitUnlimited = metrics.max_profit >= 999999999;
  const maxLossUnlimited = metrics.max_loss <= -999999999;

  return (
    <div className="grid grid-cols-2 gap-1 rounded-2xl border border-border/40 bg-surface/20 p-2 shadow-sm backdrop-blur-md sm:grid-cols-3 md:grid-cols-5">
      <StatItem
        label="Max Profit"
        value={maxProfitUnlimited ? 'Unlimited' : formatINR(metrics.max_profit)}
        valueClass="text-profit"
      />
      <StatItem
        label="Max Loss"
        value={maxLossUnlimited ? 'Unlimited' : formatINR(metrics.max_loss)}
        valueClass="text-loss"
      />
      <StatItem
        label="Breakeven(s)"
        value={
          metrics.breakevens.length > 0
            ? metrics.breakevens.map((b) => formatPrice(b)).join(', ')
            : '—'
        }
      />
      <StatItem 
        label="PoP" 
        value={formatPct(metrics.probability_of_profit)} 
      />
      <StatItem 
        label="Margin Req." 
        value={formatINR(metrics.margin_required)} 
      />
    </div>
  );
}