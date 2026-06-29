/**
 * AssumptionCard — Single assumption check card. Color-coded border and background.
 */
import type { AssumptionCheck } from '../../types/strategy';

interface Props {
  check: AssumptionCheck;
}

const STATUS_STYLES: Record<AssumptionCheck['status'], { border: string; bg: string; iconColor: string }> = {
  valid: { border: 'border-profit/30', bg: '', iconColor: 'text-profit' },
  broken: { border: 'border-loss/30', bg: 'bg-loss/5', iconColor: 'text-loss' },
  warning: { border: 'border-warning/30', bg: '', iconColor: 'text-warning' },
};

const STATUS_ICON: Record<AssumptionCheck['status'], string> = {
  valid: '✅',
  broken: '❌',
  warning: '⚠️',
};

export function AssumptionCard({ check }: Props) {
  const style = STATUS_STYLES[check.status];

  return (
    <div className={`border rounded-card p-3 ${style.border} ${style.bg} bg-surface`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={style.iconColor}>{check.icon || STATUS_ICON[check.status]}</span>
        <span className="text-primary text-sm font-medium">{check.name}</span>
      </div>
      <div className="text-secondary text-xs">{check.reason}</div>
    </div>
  );
}
