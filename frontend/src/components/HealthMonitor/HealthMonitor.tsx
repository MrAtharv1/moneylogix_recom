/**
 * HealthMonitor — Real-time health monitoring panel. Connects via WebSocket after save.
 * Shows connection status, latest diff, AI explanation, and history.
 */
import { useEffect, useState, useRef } from 'react';
import { useHealthMonitor } from '../../hooks/useWebSocket';
import { ChangeBadge } from './ChangeBadge';
import { ExplainerPanel } from '../AIExplainer/ExplainerPanel';
import { HealthTimeline } from './HealthTimeline';

interface Props {
  strategyId: string | null;
}

const STATUS_CONFIG = {
  connected: { dot: 'bg-profit', text: '● Monitoring live' },
  connecting: { dot: 'bg-warning', text: '● Connecting...' },
  disconnected: { dot: 'bg-secondary', text: '● Disconnected' },
  error: { dot: 'bg-loss', text: '● Connection error' },
};

// HELPER: Forces IST Time format
const formatISTTime = (dateString: string) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });
};

export function HealthMonitor({ strategyId }: Props) {
  const { latestEvent, connectionStatus, healthHistory } = useHealthMonitor(strategyId);
  const [explanation, setExplanation] = useState('');
  const [isExplanationLoading, setIsExplanationLoading] = useState(false);
  const lastCheckedAt = useRef<string | null>(null);

  useEffect(() => {
    if (!latestEvent) return;
    // Avoid reprocessing the same event twice.
    if (lastCheckedAt.current === latestEvent.checked_at) return;
    lastCheckedAt.current = latestEvent.checked_at;

    // Clear stale explanation immediately on a new health check, then show
    // the new one once it's available — never show a previous event's text
    // while the new one is "loading".
    setExplanation('');
    if (latestEvent.explanation) {
      setIsExplanationLoading(true);
      // explanation already arrives with the event payload; briefly show
      // loading to avoid a jarring flash, then resolve.
      const t = setTimeout(() => {
        setExplanation(latestEvent.explanation);
        setIsExplanationLoading(false);
      }, 0);
      return () => clearTimeout(t);
    }
  }, [latestEvent]);

  if (!strategyId) return null;

  const status = STATUS_CONFIG[connectionStatus];

  return (
    <div className="bg-surface border border-border rounded-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-primary text-sm font-medium">Health Monitor</h3>
        <span className="text-xs flex items-center gap-1.5 text-secondary">
          <span className={`w-2 h-2 rounded-full ${status.dot}`} />
          {status.text}
        </span>
      </div>

      {!latestEvent && (
        <div className="text-secondary text-sm">
          Monitoring started. Health check every 60 seconds.
        </div>
      )}

      {/* Safety Net: Handle WebSocket Error Messages */}
      {latestEvent && (latestEvent as any).error && (
        <div className="text-loss text-sm">
          Connection Error: {(latestEvent as any).error}
        </div>
      )}

      {latestEvent && latestEvent.diff && !latestEvent.diff.has_changes && (
        <div className="text-secondary text-sm">
          ✓ No significant changes since entry — last checked {formatISTTime(latestEvent.checked_at)}
        </div>
      )}

      {latestEvent && latestEvent.diff && latestEvent.diff.has_changes && (
        <div className="flex flex-col gap-2">
          <ChangeBadge diff={latestEvent.diff} />
          <ExplainerPanel explanation={explanation} isLoading={isExplanationLoading} />
        </div>
      )}

      <HealthTimeline history={healthHistory} />
    </div>
  );
}