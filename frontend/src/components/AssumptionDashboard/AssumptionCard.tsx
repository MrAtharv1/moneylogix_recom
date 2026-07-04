/**
 * AssumptionCard — Single assumption check card. 
 * Subtle, color-coded borders and premium typography.
 */
import type { AssumptionCheck } from '../../types/strategy';

interface Props {
  check: AssumptionCheck;
}

const STATUS_STYLES: Record<AssumptionCheck['status'], { border: string; bg: string; iconColor: string }> = {
  valid: { border: 'border-profit/20', bg: 'hover:bg-profit/5', iconColor: 'text-profit' },
  broken: { border: 'border-loss/30', bg: 'bg-loss/5 hover:bg-loss/10', iconColor: 'text-loss' },
  warning: { border: 'border-warning/30', bg: 'hover:bg-warning/5', iconColor: 'text-warning' },
};

const STATUS_ICON: Record<AssumptionCheck['status'], string> = {
  valid: '✓',
  broken: '✕',
  warning: '!',
};

export function AssumptionCard({ check }: Props) {
  const style = STATUS_STYLES[check.status];

  return (
    <div className={`flex flex-col rounded-xl border ${style.border} bg-surface/20 p-4 shadow-sm backdrop-blur-md transition-colors ${style.bg}`}>
      <div className="mb-1.5 flex items-center gap-2.5">
        <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${style.border} bg-background/50 text-[10px] font-bold ${style.iconColor}`}>
          {check.icon || STATUS_ICON[check.status]}
        </div>
        <span className="text-sm font-medium text-primary">{check.name}</span>
      </div>
      <div className="pl-7 text-xs leading-relaxed text-secondary/80">{check.reason}</div>
    </div>
  );
}