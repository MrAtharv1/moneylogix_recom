/**
 * DataModeBanner — Always-visible indicator of which data tier is active.
 * Shows at top of page. Users always know if they're on live or demo data.
 */
import type { DataMode, DataModeType } from '../../types/strategy';

interface Props {
  dataMode: DataMode | null;
}

interface BannerConfig {
  bg: string;
  border: string;
  dot: string;
  text: string;
}

export function DataModeBanner({ dataMode }: Props) {
  if (!dataMode) return null;

  const configs: Record<DataModeType, BannerConfig> = {
    live: {
      bg: 'bg-profit/10',
      border: 'border-profit/30',
      dot: 'bg-profit',
      text: '● Live Data',
    },
    cached: {
      bg: 'bg-accent/10',
      border: 'border-accent/30',
      dot: 'bg-accent',
      text: `● Cached Data (as of ${dataMode.timestamp ? new Date(dataMode.timestamp).toLocaleTimeString() : '—'})`,
    },
    snapshot: {
      bg: 'bg-warning/10',
      border: 'border-warning/30',
      dot: 'bg-warning',
      text: '⚠ Snapshot Data — NSE unavailable',
    },
    demo: {
      bg: 'bg-orange-500/10',
      border: 'border-orange-500/30',
      dot: 'bg-orange-500',
      text: 'Demo Mode — using sample data. Full functionality preserved.',
    },
  };

  const config = configs[dataMode.mode];

  return (
    <div className={`w-full px-4 py-1.5 text-xs flex items-center gap-2 border-b ${config.bg} ${config.border}`}>
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      <span className="text-secondary">{config.text}</span>
    </div>
  );
}
