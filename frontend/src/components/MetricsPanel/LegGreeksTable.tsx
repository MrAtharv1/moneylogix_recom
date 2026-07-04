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
      <div className="flex flex-col gap-1 rounded-2xl border border-border/40 bg-surface/20 p-4 shadow-sm">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-10 w-full animate-pulse rounded-lg bg-border/30" />
        ))}
      </div>
    );
  }

  if (legs.length === 0 || greeksPerLeg.length === 0) {
    return (
      <div className="flex h-24 items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Run analysis to view leg-level Greeks
      </div>
    );
  }

  const rows = legs
    .map((leg, i) => ({ leg, greeks: greeksPerLeg[i] }))
    .filter((row) => row.greeks !== undefined)
    .sort((a, b) => a.leg.strike - b.leg.strike);

  return (
    <div className="overflow-hidden rounded-2xl border border-border/40 bg-surface/20 shadow-sm backdrop-blur-md">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <thead className="bg-surface/30">
            <tr className="border-b border-border/40 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">
              <th className="py-3 pl-4 pr-3">Strike</th>
              <th className="py-3 pr-3">Type</th>
              <th className="py-3 pr-3">Side</th>
              <th className="py-3 pr-3 text-right">Delta</th>
              <th className="py-3 pr-3 text-right">Theta</th>
              <th className="py-3 pr-3 text-right">Price</th>
              <th className="py-3 pl-3 pr-4 text-right">PoP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/20">
            {rows.map(({ leg, greeks }) => (
              <tr key={leg.id} className="transition-colors hover:bg-surface/40">
                <td className="py-2.5 pl-4 pr-3 font-medium tabular-nums text-primary">{leg.strike}</td>
                <td className="py-2.5 pr-3 capitalize text-secondary">{leg.option_type}</td>
                <td className="py-2.5 pr-3 capitalize text-secondary">
                  <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                    leg.side === 'buy' ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'
                  }`}>
                    {leg.side}
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-right tabular-nums text-primary">{formatDelta(greeks.delta)}</td>
                <td className="py-2.5 pr-3 text-right tabular-nums text-primary">{formatTheta(greeks.theta)}</td>
                <td className="py-2.5 pr-3 text-right tabular-nums font-medium text-primary">{formatINR(greeks.price)}</td>
                <td className="py-2.5 pl-3 pr-4 text-right tabular-nums text-primary">{formatPct(greeks.pop)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}