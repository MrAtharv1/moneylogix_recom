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
  connected: { dot: 'bg-profit', glow: 'shadow-[0_0_8px_rgba(47,191,113,0.6)]', text: 'Monitoring live' },
  connecting: { dot: 'bg-warning', glow: 'shadow-[0_0_8px_rgba(245,166,35,0.6)]', text: 'Connecting...' },
  disconnected: { dot: 'bg-secondary/50', glow: '', text: 'Disconnected' },
  error: { dot: 'bg-loss', glow: 'shadow-[0_0_8px_rgba(226,85,85,0.6)]', text: 'Connection error' },
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
    if (lastCheckedAt.current === latestEvent.checked_at) return;
    lastCheckedAt.current = latestEvent.checked_at;

    setExplanation('');
    if (latestEvent.explanation) {
      setIsExplanationLoading(true);
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
    <div className="flex flex-col rounded-2xl border border-border/40 bg-surface/20 p-5 shadow-sm backdrop-blur-md transition-all">
      <div className="mb-4 flex items-center justify-between border-b border-border/30 pb-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Health Monitor</h3>
        <div className="flex items-center gap-2 rounded-full border border-border/40 bg-surface/30 px-2.5 py-1 shadow-sm">
          <span className={`h-1.5 w-1.5 rounded-full ${status.dot} ${status.glow}`} />
          <span className="text-[10px] font-medium uppercase tracking-wide text-secondary/80">{status.text}</span>
        </div>
      </div>

      {!latestEvent && (
        <div className="flex h-20 items-center justify-center rounded-xl border border-dashed border-border/50 bg-surface/10 text-[13px] text-secondary/60">
          Monitoring initialized. Checking health every 60 seconds.
        </div>
      )}

      {/* Safety Net: Handle WebSocket Error Messages */}
      {latestEvent && (latestEvent as any).error && (
        <div className="rounded-xl border border-loss/20 bg-loss/5 p-3 text-sm text-loss">
          Connection Error: {(latestEvent as any).error}
        </div>
      )}

      {latestEvent && latestEvent.diff && !latestEvent.diff.has_changes && (
        <div className="flex items-center gap-2 rounded-xl bg-surface/30 px-4 py-3 text-[13px] text-secondary/80">
          <span className="text-profit">✓</span>
          Stable — last checked at <span className="font-medium tabular-nums">{formatISTTime(latestEvent.checked_at)}</span>
        </div>
      )}

      {latestEvent && latestEvent.diff && latestEvent.diff.has_changes && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2.5 rounded-xl border border-border/30 bg-surface/10 p-4">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-secondary/60">Detected Changes</span>
            <ChangeBadge diff={latestEvent.diff} />
          </div>
          <ExplainerPanel explanation={explanation} isLoading={isExplanationLoading} />
        </div>
      )}

      <HealthTimeline history={healthHistory} />
    </div>
  );
}