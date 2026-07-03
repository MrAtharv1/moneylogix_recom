/**
 * LegRow — Single editable leg row with copilot hint below it.
 */
import { useState, useEffect, useRef } from 'react';
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

    // Skip if nothing actually changed
    if (JSON.stringify(prevLegRef.current) === JSON.stringify(leg)) {
      return;
    }
    prevLegRef.current = leg;

    setHint('');
    setIsHintLoading(true);
    clearTimeout(debounceTimer.current);

    debounceTimer.current = setTimeout(async () => {
      try {
        const result = await getCopilotHint({
          changed_leg_before: prevLegRef.current,
          changed_leg_after: leg,
          metrics_before: metricsBeforeChange || {},
          metrics_after: {}
        });
        setHint(result);
      } catch (e) {
        setHint('');
      } finally {
        setIsHintLoading(false);
      }
    }, 300);

    return () => clearTimeout(debounceTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leg.strike, leg.expiry, leg.option_type, leg.side, leg.quantity, leg.iv]);

  return (
    <div className="border border-border rounded-card p-3 bg-surface">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-secondary text-xs w-5">{index + 1}</span>

        <input
          type="number"
          value={leg.strike}
          onChange={(e) => onUpdate({ strike: Number(e.target.value) })}
          className="bg-background border border-border rounded-control px-2 py-1 text-sm w-24 text-primary"
          aria-label="Strike"
        />

        <input
          type="date"
          value={leg.expiry}
          onChange={(e) => onUpdate({ expiry: e.target.value })}
          className="bg-background border border-border rounded-control px-2 py-1 text-sm text-primary"
          aria-label="Expiry"
        />

        <select
          value={leg.option_type}
          onChange={(e) => onUpdate({ option_type: e.target.value as OptionType })}
          className="bg-background border border-border rounded-control px-2 py-1 text-sm text-primary"
          aria-label="Option type"
        >
          <option value="call">Call</option>
          <option value="put">Put</option>
        </select>

        <select
          value={leg.side}
          onChange={(e) => onUpdate({ side: e.target.value as Side })}
          className="bg-background border border-border rounded-control px-2 py-1 text-sm text-primary"
          aria-label="Side"
        >
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
        </select>

        <input
          type="number"
          min={1}
          value={leg.quantity}
          onChange={(e) => onUpdate({ quantity: Number(e.target.value) })}
          className="bg-background border border-border rounded-control px-2 py-1 text-sm w-16 text-primary"
          aria-label="Quantity (lots)"
        />

        <input
          type="number"
          step={0.1}
          value={Number((leg.iv * 100).toFixed(1))}
          onChange={(e) => onUpdate({ iv: Number(e.target.value) / 100 })}
          className="bg-background border border-border rounded-control px-2 py-1 text-sm w-20 text-primary"
          aria-label="IV (percentage)"
        />

        <button
          onClick={onDelete}
          className="ml-auto text-loss text-xs px-2 py-1 rounded-control hover:bg-loss/10"
          aria-label="Remove leg"
        >
          Remove
        </button>
      </div>

      <CopilotHint hint={hint} isLoading={isHintLoading} />
    </div>
  );
}