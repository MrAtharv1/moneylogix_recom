import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { getCopilotHint } from '../../api/client';
import type { Leg, OptionType, Side } from '../../types/strategy';
import { CopilotHint } from './CopilotHint';

interface Props {
  leg: Leg;
  index: number;
  metricsBeforeChange?: unknown;
  onUpdate: (updates: Partial<Leg>) => void;
  onDelete: () => void;
}

export function LegRow({ leg, index, metricsBeforeChange, onUpdate, onDelete }: Props) {
  const [hint, setHint] = useState('');
  const [isHintLoading, setIsHintLoading] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const isFirstRender = useRef(true);
  const prevLegRef = useRef<Leg>(leg);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      prevLegRef.current = leg;
      return;
    }

    if (JSON.stringify(prevLegRef.current) === JSON.stringify(leg)) {
      return;
    }

    const legBefore = prevLegRef.current;
    prevLegRef.current = leg;

    setHint('');
    setIsHintLoading(true);
    clearTimeout(debounceTimer.current);

    // Create an AbortController for this specific request
    const abortController = new AbortController();

    debounceTimer.current = setTimeout(async () => {
      try {
        const result = await getCopilotHint(
          {
            changed_leg_before: legBefore,
            changed_leg_after: leg,
            metrics_before: metricsBeforeChange || {},
            metrics_after: {}
          },
          abortController.signal // Pass signal to client
        );
        setHint(result);
      } catch (e: any) {
        // Ignore aborted request errors, otherwise clear hint
        if (e.name !== 'CanceledError' && e.message !== 'canceled') {
          setHint('');
        }
      } finally {
        if (!abortController.signal.aborted) {
          setIsHintLoading(false);
        }
      }
    }, 300);

    // Cleanup: clear timer and abort in-flight requests if component unmounts or leg updates rapidly
    return () => {
      clearTimeout(debounceTimer.current);
      abortController.abort();
    };
  }, [leg, metricsBeforeChange]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -15, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="group flex flex-col gap-1.5"
    >
      <div className="relative rounded-xl ring-1 ring-white/5 bg-surface/20 p-1.5 shadow-sm transition-all hover:ring-white/10 hover:bg-white/5">
        <div className="grid grid-cols-[24px_minmax(84px,1fr)_minmax(120px,1.2fr)_minmax(80px,0.8fr)_minmax(80px,0.8fr)_minmax(60px,0.65fr)_minmax(70px,0.7fr)_28px] items-center gap-1.5 overflow-x-auto pb-0">
          <span 
            title="Leg Number"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-background/50 text-[11px] font-medium text-secondary/70 shadow-inner cursor-help"
          >
            {index + 1}
          </span>
          <input
            title="Strike Price"
            type="number"
            value={leg.strike || ''}
            onChange={(e) => {
              const val = e.target.value === '' ? 0 : Number(e.target.value);
              if (!isNaN(val)) onUpdate({ strike: val });
            }}
            className="h-8 w-full rounded-md border-transparent bg-transparent px-2 text-sm tabular-nums text-primary transition-colors placeholder:text-secondary/50 hover:bg-surface focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/50"
            aria-label="Strike"
            placeholder="Strike"
          />
          <input
            title="Expiry Date"
            type="date"
            // Slicing to guarantee YYYY-MM-DD format
            value={leg.expiry.split('T')[0]}
            onChange={(e) => onUpdate({ expiry: e.target.value })}
            className="h-8 w-full rounded-md border-transparent bg-transparent px-2 text-sm text-primary transition-colors hover:bg-surface focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/50"
            aria-label="Expiry"
          />
          <select
            title="Option Type (Call/Put)"
            value={leg.option_type}
            onChange={(e) => onUpdate({ option_type: e.target.value as OptionType })}
            className="h-8 w-full appearance-none rounded-md border-transparent bg-transparent px-2 text-sm text-primary transition-colors hover:bg-surface focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/50 cursor-pointer"
          >
            <option value="call">Call</option>
            <option value="put">Put</option>
          </select>
          <select
            title="Trade Side (Buy/Sell)"
            value={leg.side}
            onChange={(e) => onUpdate({ side: e.target.value as Side })}
            className="h-8 w-full appearance-none rounded-md border-transparent bg-transparent px-2 text-sm text-primary transition-colors hover:bg-surface focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/50 cursor-pointer"
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
          <input
            title="Quantity (Number of Lots)"
            type="number"
            min={1}
            value={leg.quantity}
            onChange={(e) => {
              const val = e.target.value === '' ? 1 : Number(e.target.value);
              if (!isNaN(val) && val >= 1) onUpdate({ quantity: val });
            }}
            className="h-8 w-full rounded-md border-transparent bg-transparent px-2 text-sm tabular-nums text-primary transition-colors hover:bg-surface focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/50"
            aria-label="Quantity"
            placeholder="Qty"
          />
          <input
            title="Implied Volatility (IV %)"
            type="number"
            step={0.1}
            value={Number((leg.iv * 100).toFixed(1))}
            onChange={(e) => {
              const val = e.target.value === '' ? 0 : Number(e.target.value);
              if (!isNaN(val)) onUpdate({ iv: val / 100 });
            }}
            className="h-8 w-full rounded-md border-transparent bg-transparent px-2 text-sm tabular-nums text-primary transition-colors hover:bg-surface focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent/50"
            aria-label="IV %"
            placeholder="IV %"
          />
          <button
            title="Remove Leg"
            onClick={onDelete}
            className="flex h-7 w-7 items-center justify-center rounded-md text-secondary/40 transition-colors hover:bg-loss/10 hover:text-loss focus:outline-none focus:ring-2 focus:ring-loss/30"
            aria-label="Remove leg"
          >
            ✕
          </button>
        </div>
      </div>
      <CopilotHint hint={hint} isLoading={isHintLoading} />
    </motion.div>
  );
}