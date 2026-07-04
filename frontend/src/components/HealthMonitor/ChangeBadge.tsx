/**
 * ChangeBadge — Pill badges showing what changed in the health monitor.
 * Sleek, tabular, Linear-inspired badges.
 */
import type { HealthDiff } from '../../types/strategy';
import { formatINR } from '../../utils/formatters';

interface Props {
  diff: HealthDiff;
}

function Pill({ children, colorClass }: { children: React.ReactNode; colorClass: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium tracking-wide tabular-nums shadow-sm ${colorClass}`}>
      {children}
    </span>
  );
}

export function ChangeBadge({ diff }: Props) {
  const badges: React.ReactNode[] = [];

  if (diff.iv) {
    const isUp = diff.iv.direction === 'up' || diff.iv.change > 0;
    badges.push(
      <Pill
        key="iv"
        colorClass={isUp ? 'border-warning/20 bg-warning/5 text-warning' : 'border-accent/20 bg-accent/5 text-accent'}
      >
        <span>IV</span>
        <span className="font-semibold">{isUp ? '↑' : '↓'} {Math.abs(diff.iv.change).toFixed(1)}pp</span>
      </Pill>
    );
  }

  if (diff.price) {
    const isUp = diff.price.pct >= 0;
    badges.push(
      <Pill
        key="price"
        colorClass={isUp ? 'border-profit/20 bg-profit/5 text-profit' : 'border-loss/20 bg-loss/5 text-loss'}
      >
        <span>Underlying</span>
        <span className="font-semibold">{isUp ? '↑' : '↓'} {Math.abs(diff.price.pct).toFixed(1)}%</span>
      </Pill>
    );
  }

  if (diff.pnl) {
    const isUp = diff.pnl.change >= 0;
    badges.push(
      <Pill
        key="pnl"
        colorClass={isUp ? 'border-profit/20 bg-profit/5 text-profit' : 'border-loss/20 bg-loss/5 text-loss'}
      >
        <span>P&amp;L</span>
        <span className="font-semibold">{isUp ? '▲' : '▼'} {formatINR(Math.abs(diff.pnl.change))}</span>
      </Pill>
    );
  }

  if (diff.dte_warning) {
    badges.push(
      <Pill key="dte" colorClass="border-warning/30 bg-warning/10 text-warning">
        <span className="font-bold">⚠</span> &lt;7 days to expiry
      </Pill>
    );
  }

  if (badges.length === 0) return null;

  return <div className="flex flex-wrap gap-2">{badges}</div>;
}