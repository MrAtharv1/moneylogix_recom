/**
 * ChangeBadge — Pill badges showing what changed in the health monitor.
 * Compact, color-coded, display-ready.
 */
import type { HealthDiff } from '../../types/strategy';
import { formatINR } from '../../utils/formatters';

interface Props {
  diff: HealthDiff;
}

function Pill({ children, colorClass }: { children: React.ReactNode; colorClass: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-mono border ${colorClass}`}>
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
        colorClass={isUp ? 'text-warning border-warning/30 bg-background' : 'text-accent border-accent/30 bg-background'}
      >
        IV {isUp ? '↑' : '↓'}
        {Math.abs(diff.iv.change).toFixed(1)}pp
      </Pill>
    );
  }

  if (diff.price) {
    const isUp = diff.price.pct >= 0;
    badges.push(
      <Pill
        key="price"
        colorClass={isUp ? 'text-profit border-profit/30 bg-background' : 'text-loss border-loss/30 bg-background'}
      >
        Underlying {isUp ? '↑' : '↓'}
        {Math.abs(diff.price.pct).toFixed(1)}%
      </Pill>
    );
  }

  if (diff.pnl) {
    const isUp = diff.pnl.change >= 0;
    badges.push(
      <Pill
        key="pnl"
        colorClass={isUp ? 'text-profit border-profit/30 bg-background' : 'text-loss border-loss/30 bg-background'}
      >
        P&amp;L {isUp ? '▲' : '▼'} {formatINR(Math.abs(diff.pnl.change))}
      </Pill>
    );
  }

  if (diff.dte_warning) {
    badges.push(
      <Pill key="dte" colorClass="text-warning border-warning/30 bg-background">
        ⚠ &lt;7 days to expiry
      </Pill>
    );
  }

  if (badges.length === 0) return null;

  return <div className="flex flex-wrap gap-2">{badges}</div>;
}
