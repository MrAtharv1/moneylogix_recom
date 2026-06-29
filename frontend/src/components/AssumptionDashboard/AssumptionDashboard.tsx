/**
 * AssumptionDashboard — 2×2 grid of AssumptionCards with score below.
 * Shows skeleton cards while loading.
 */
import type { AssumptionResult } from '../../types/strategy';
import { AssumptionCard } from './AssumptionCard';

interface Props {
  result: AssumptionResult | null;
  isLoading: boolean;
}

function SkeletonCard() {
  return (
    <div className="border border-border rounded-card p-3 bg-surface">
      <div className="skeleton h-4 w-2/3 mb-2" />
      <div className="skeleton h-3 w-full" />
    </div>
  );
}

export function AssumptionDashboard({ result, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (!result) {
    return <div className="text-secondary text-sm p-4">Run analysis to check strategy assumptions</div>;
  }

  const scoreText =
    result.total_count > 0
      ? `${result.valid_count}/${result.total_count} assumptions currently valid`
      : 'N/A for custom strategies';

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        {result.checks.map((check, i) => (
          <AssumptionCard key={`${check.name}-${i}`} check={check} />
        ))}
      </div>
      <div className="text-secondary text-sm">{result.score_display || scoreText}</div>
    </div>
  );
}
