/**
 * AssumptionDashboard — 2×2 grid of AssumptionCards with score below.
 * Refined premium layout.
 */
import type { AssumptionResult } from '../../types/strategy';
import { AssumptionCard } from './AssumptionCard';

interface Props {
  result: AssumptionResult | null;
  isLoading: boolean;
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border/40 bg-surface/20 p-4 shadow-sm">
      <div className="mb-3 h-4 w-2/3 animate-pulse rounded bg-border/50" />
      <div className="h-3 w-full animate-pulse rounded bg-border/30" />
    </div>
  );
}

export function AssumptionDashboard({ result, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Run analysis to check strategy assumptions
      </div>
    );
  }

  const scoreText =
    result.total_count > 0
      ? `${result.valid_count}/${result.total_count} assumptions currently valid`
      : 'N/A for custom strategies';

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {result.checks.map((check, i) => (
          <AssumptionCard key={`${check.name}-${i}`} check={check} />
        ))}
      </div>
      <div className="px-1 text-[11px] font-medium uppercase tracking-wider text-secondary/60">
        {result.score_display || scoreText}
      </div>
    </div>
  );
}