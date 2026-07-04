// // /**
// //  * DataModeBanner — Always-visible indicator of which data tier is active.
// //  * Refined to look like a premium system-level banner.
// //  */
// // import type { DataMode, DataModeType } from '../../types/strategy';

// // interface Props {
// //   dataMode: DataMode | null;
// // }

// // interface BannerConfig {
// //   bg: string;
// //   border: string;
// //   dot: string;
// //   text: string;
// // }

// // export function DataModeBanner({ dataMode }: Props) {
// //   if (!dataMode) return null;

// //   const configs: Record<DataModeType, BannerConfig> = {
// //     live: {
// //       bg: 'bg-profit/5',
// //       border: 'border-profit/20',
// //       dot: 'bg-profit',
// //       text: 'Live Data',
// //     },
// //     cached: {
// //       bg: 'bg-accent/5',
// //       border: 'border-accent/20',
// //       dot: 'bg-accent',
// //       text: `Cached Data (as of ${dataMode.timestamp ? new Date(dataMode.timestamp).toLocaleTimeString() : '—'})`,
// //     },
// //     snapshot: {
// //       bg: 'bg-warning/5',
// //       border: 'border-warning/20',
// //       dot: 'bg-warning',
// //       text: 'Snapshot Data — NSE unavailable',
// //     },
// //     demo: {
// //       bg: 'bg-[#f97316]/5', // Tailwind orange-500 equivalent with opacity
// //       border: 'border-[#f97316]/20',
// //       dot: 'bg-[#f97316]',
// //       text: 'Demo Mode — Sample data. Full functionality preserved.',
// //     },
// //   };

// //   const config = configs[dataMode.mode];

// //   return (
// //     <div className={`flex w-full items-center justify-center gap-2 border-b px-4 py-2 text-[11px] font-medium uppercase tracking-wider backdrop-blur-md transition-colors ${config.bg} ${config.border}`}>
// //       <span className="relative flex h-1.5 w-1.5">
// //         <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${config.dot}`}></span>
// //         <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${config.dot}`}></span>
// //       </span>
// //       <span className="text-secondary/80">{config.text}</span>
// //     </div>
// //   );
// // }

// /**
//  * DataModeBanner — Always-visible indicator of which data tier is active.
//  * Refined to look like a premium system-level banner.
//  */
// import type { DataMode, DataModeType } from '../../types/strategy';

// interface Props {
//   dataMode: DataMode | null;
// }

// interface BannerConfig {
//   bg: string;
//   border: string;
//   dot: string;
//   text: string;
// }

// export function DataModeBanner({ dataMode }: Props) {
//   if (!dataMode) return null;

//   const configs: Partial<Record<DataModeType, BannerConfig>> = {
//     live: {
//       bg: 'bg-profit/5',
//       border: 'border-profit/20',
//       dot: 'bg-profit',
//       text: 'Live Data',
//     },
//     cached: {
//       bg: 'bg-accent/5',
//       border: 'border-accent/20',
//       dot: 'bg-accent',
//       text: `Cached Data (as of ${dataMode.timestamp ? new Date(dataMode.timestamp).toLocaleTimeString() : '—'})`,
//     },
//     snapshot: {
//       bg: 'bg-warning/5',
//       border: 'border-warning/20',
//       dot: 'bg-warning',
//       text: 'Snapshot Data — NSE unavailable',
//     },
//     // Demo mode intentionally removed. 
//   };

//   const config = configs[dataMode.mode];
  
//   // If the backend sends 'demo' (or any unmapped mode), hide the banner completely.
//   if (!config) return null; 

//   return (
//     <div className={`flex w-full items-center justify-center gap-2 border-b px-4 py-2 text-[11px] font-medium uppercase tracking-wider backdrop-blur-md transition-colors ${config.bg} ${config.border}`}>
//       <span className="relative flex h-1.5 w-1.5">
//         <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${config.dot}`}></span>
//         <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${config.dot}`}></span>
//       </span>
//       <span className="text-secondary/80">{config.text}</span>
//     </div>
//   );
// }

/**
 * DataModeBanner — Always-visible indicator of which data tier is active.
 * Refined to look like a premium system-level banner.
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

  const configs: Partial<Record<DataModeType, BannerConfig>> = {
    live: {
      bg: 'bg-profit/5',
      border: 'border-profit/20',
      dot: 'bg-profit',
      text: 'Live Data',
    },
    cached: {
      bg: 'bg-accent/5',
      border: 'border-accent/20',
      dot: 'bg-accent',
      text: `Cached Data (as of ${dataMode.timestamp ? new Date(dataMode.timestamp).toLocaleTimeString() : '—'})`,
    },
    // 'snapshot' and 'demo' are intentionally omitted. 
    // If the backend returns them, the banner will silently hide itself.
  };

  const config = configs[dataMode.mode];
  
  if (!config) return null; 

  return (
    <div className={`flex w-full items-center justify-center gap-2 border-b px-4 py-2 text-[11px] font-medium uppercase tracking-wider backdrop-blur-md transition-colors ${config.bg} ${config.border}`}>
      <span className="relative flex h-1.5 w-1.5">
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${config.dot}`}></span>
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${config.dot}`}></span>
      </span>
      <span className="text-secondary/80">{config.text}</span>
    </div>
  );
}