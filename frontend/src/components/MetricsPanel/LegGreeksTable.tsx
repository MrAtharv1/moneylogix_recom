/**
 * LegGreeksTable — Table with: Strike | Type | Side | Delta | Theta | Price | PoP
 * One row per leg. Sort by strike ascending.
 */
import type { Leg, Greeks } from '../../types/strategy';
import { formatDelta, formatTheta, formatINR, formatPct } from '../../utils/formatters';

interface Props {
  legs: Leg[];
  greeksPerLeg: Greeks[];
  isLoading: boolean;
}

export function LegGreeksTable({ legs, greeksPerLeg, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="skeleton h-8 w-full" />
        ))}
      </div>
    );
  }

  if (legs.length === 0 || greeksPerLeg.length === 0) {
    return <div className="text-secondary text-sm p-4">Run analysis to see per-leg Greeks</div>;
  }

  const rows = legs
    .map((leg, i) => ({ leg, greeks: greeksPerLeg[i] }))
    .filter((row) => row.greeks !== undefined)
    .sort((a, b) => a.leg.strike - b.leg.strike);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-secondary text-xs text-left border-b border-border">
            <th className="py-2 pr-3 font-normal">Strike</th>
            <th className="py-2 pr-3 font-normal">Type</th>
            <th className="py-2 pr-3 font-normal">Side</th>
            <th className="py-2 pr-3 font-normal">Delta</th>
            <th className="py-2 pr-3 font-normal">Theta</th>
            <th className="py-2 pr-3 font-normal">Price</th>
            <th className="py-2 pr-3 font-normal">PoP</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ leg, greeks }) => (
            <tr key={leg.id} className="border-b border-border/50">
              <td className="py-2 pr-3 text-primary">{leg.strike}</td>
              <td className="py-2 pr-3 text-secondary capitalize">{leg.option_type}</td>
              <td className="py-2 pr-3 text-secondary capitalize">{leg.side}</td>
              <td className="py-2 pr-3 text-primary">{formatDelta(greeks.delta)}</td>
              <td className="py-2 pr-3 text-primary">{formatTheta(greeks.theta)}</td>
              <td className="py-2 pr-3 text-primary">{formatINR(greeks.price)}</td>
              <td className="py-2 pr-3 text-primary">{formatPct(greeks.pop)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
