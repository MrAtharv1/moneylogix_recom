/**
 * PortfolioGreeks — Net Delta, Net Gamma, Net Theta, Net Vega
 * Layout: 4 cards in a row. Each card has a plain-English subtitle.
 */
import type { PortfolioGreeks as PortfolioGreeksType } from '../../types/strategy';
import { formatDelta, formatTheta } from '../../utils/formatters';

interface Props {
  greeks: PortfolioGreeksType | null;
  isLoading: boolean;
}

const GREEK_SUBTITLES: Record<string, string> = {
  delta: 'Directional exposure to price moves',
  gamma: 'How fast delta changes',
  theta: 'Time decay per day',
  vega: 'Sensitivity to volatility changes',
};

function GreekCard({ label, value, subtitle }: { label: string; value: string; subtitle: string }) {
  return (
    <div className="bg-surface border border-border rounded-card p-3 flex-1">
      <div className="text-secondary text-xs mb-1">{label}</div>
      <div className="text-lg font-semibold text-primary">{value}</div>
      <div className="text-secondary text-xs mt-1">{subtitle}</div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-surface border border-border rounded-card p-3 flex-1">
      <div className="skeleton h-3 w-16 mb-2" />
      <div className="skeleton h-5 w-12 mb-2" />
      <div className="skeleton h-3 w-full" />
    </div>
  );
}

export function PortfolioGreeks({ greeks, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (!greeks) {
    return <div className="text-secondary text-sm p-4">Run analysis to see portfolio Greeks</div>;
  }

  return (
    <div className="flex gap-3">
      <GreekCard label="Net Delta" value={formatDelta(greeks.net_delta)} subtitle={GREEK_SUBTITLES.delta} />
      <GreekCard label="Net Gamma" value={greeks.net_gamma.toFixed(4)} subtitle={GREEK_SUBTITLES.gamma} />
      <GreekCard label="Net Theta" value={formatTheta(greeks.net_theta)} subtitle={GREEK_SUBTITLES.theta} />
      <GreekCard label="Net Vega" value={greeks.net_vega.toFixed(2)} subtitle={GREEK_SUBTITLES.vega} />
    </div>
  );
}
