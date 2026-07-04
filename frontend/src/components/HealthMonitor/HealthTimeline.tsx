/**
 * HealthTimeline — Activity feed for the health monitor.
 * Transformed into a vertical trace-line UI.
 * Now shows a placeholder when empty.
 */
import { useState } from 'react';

interface Props {
  history: any[];
}

// HELPER: Forces IST Date & Time format (e.g., 02/07/2026, 07:57:32 pm)
const formatISTDateTime = (dateString: string) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
};

export function HealthTimeline({ history }: Props) {
  const [showHistory, setShowHistory] = useState(true);

  // Always render the container – no more early `return null`
  return (
    <div className="mt-5 flex flex-col gap-4 border-t border-border/30 pt-5">
      <button
        onClick={() => setShowHistory(!showHistory)}
        className="w-fit text-[11px] font-semibold uppercase tracking-wider text-secondary/70 transition-colors hover:text-primary"
      >
        {showHistory ? 'Hide Event Log' : 'View Event Log'}
      </button>

      {showHistory && (
        <div className="relative flex max-h-64 flex-col overflow-y-auto pl-2 pr-2">
          {/* Vertical tracking line – always visible */}
          <div className="absolute bottom-4 left-[11px] top-4 w-[1px] bg-border/40" />

          {history.length === 0 ? (
            // ─── Placeholder when no events exist ──────────────────────────
            <div className="py-4 pl-6 text-sm text-secondary/60">
              No health events recorded yet. The monitor will log changes as they happen.
            </div>
          ) : (
            // ─── Render the event list ──────────────────────────────────────
            history.map((item, i) => (
              <div
                key={i}
                className="group relative flex flex-col gap-1 py-3 pl-6 transition-colors hover:bg-surface/10 rounded-lg"
              >
                {/* Timeline Dot */}
                <div className="absolute left-[9px] top-[18px] h-1.5 w-1.5 rounded-full bg-border/60 transition-colors group-hover:bg-accent" />

                <div className="text-[11px] font-medium tabular-nums text-secondary/60">
                  {formatISTDateTime(item.checked_at || item.timestamp)}
                </div>

                <div
                  className={`text-[13px] ${
                    item.diff && item.diff.has_changes
                      ? 'text-primary'
                      : 'text-secondary/80'
                  }`}
                >
                  {item.diff && item.diff.has_changes
                    ? 'Changes detected in strategy health.'
                    : 'No significant changes.'}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}