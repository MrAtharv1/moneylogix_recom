/**
 * PortfolioGreeks — Net Delta, Net Gamma, Net Theta, Net Vega
 * Layout: Unified strip with internal dividers
 */
import type { PortfolioGreeks as PortfolioGreeksType } from '../../types/strategy';
import { formatDelta, formatTheta } from '../../utils/formatters';

interface Props {
  greeks: PortfolioGreeksType | null;
  isLoading: boolean;
}

const GREEK_SUBTITLES: Record<string, string> = {
  delta: 'Directional exposure',
  gamma: 'Delta sensitivity',
  theta: 'Daily time decay',
  vega: 'Vol sensitivity',
};

function GreekItem({ label, value, subtitle }: { label: string; value: string; subtitle: string }) {
  return (
    <div className="flex flex-1 flex-col justify-center border-r border-border/30 p-4 last:border-r-0 hover:bg-surface/30 transition-colors">
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">{label}</div>
      <div className="text-lg font-semibold tabular-nums tracking-tight text-primary">{value}</div>
      <div className="mt-1 text-[11px] text-secondary/50">{subtitle}</div>
    </div>
  );
}

function SkeletonItem() {
  return (
    <div className="flex-1 border-r border-border/30 p-4 last:border-r-0">
      <div className="mb-2 h-2.5 w-12 animate-pulse rounded bg-border/50" />
      <div className="mb-2 h-6 w-16 animate-pulse rounded bg-border/50" />
      <div className="h-2 w-20 animate-pulse rounded bg-border/30" />
    </div>
  );
}

export function PortfolioGreeks({ greeks, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex w-full overflow-hidden rounded-2xl border border-border/40 bg-surface/20 shadow-sm">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonItem key={i} />
        ))}
      </div>
    );
  }

  if (!greeks) {
    return (
      <div className="flex h-24 items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Run analysis to view portfolio Greeks
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col overflow-hidden rounded-2xl border border-border/40 bg-surface/20 shadow-sm backdrop-blur-md sm:flex-row">
      <GreekItem label="Net Delta" value={formatDelta(greeks.net_delta)} subtitle={GREEK_SUBTITLES.delta} />
      <GreekItem label="Net Gamma" value={greeks.net_gamma.toFixed(4)} subtitle={GREEK_SUBTITLES.gamma} />
      <GreekItem label="Net Theta" value={formatTheta(greeks.net_theta)} subtitle={GREEK_SUBTITLES.theta} />
      <GreekItem label="Net Vega" value={greeks.net_vega.toFixed(2)} subtitle={GREEK_SUBTITLES.vega} />
    </div>
  );
}