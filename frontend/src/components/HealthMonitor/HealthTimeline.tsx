/**
 * HealthTimeline — Collapsed by default. Expand on user click to show past events.
 */
import { useState } from 'react';
import type { HealthEvent } from '../../types/strategy';
import { ChangeBadge } from './ChangeBadge';

interface Props {
  history: HealthEvent[];
}

export function HealthTimeline({ history }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (history.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="text-secondary text-xs hover:text-primary transition-colors"
      >
        {expanded ? 'Hide history' : `Show history (${history.length} events)`}
      </button>

      {expanded && (
        <div className="flex flex-col gap-2 mt-2">
          {history.map((event, i) => (
            <div key={i} className="border-t border-border pt-2">
              <div className="text-secondary text-xs mb-1">
                {new Date(event.checked_at).toLocaleString()}
              </div>
              {event.diff.has_changes ? (
                <ChangeBadge diff={event.diff} />
              ) : (
                <span className="text-secondary text-xs">No significant changes</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
