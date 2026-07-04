import { useState } from 'react';
import { useOptionChain } from '../../hooks/useOptionChain';

interface Props {
  symbol: string;
  onStrikeSelect: (strike: number, optionType: 'call' | 'put') => void;
}

export function StrikeLadder({ symbol, onStrikeSelect }: Props) {
  const { chain, isLoading } = useOptionChain(symbol);
  const [isOpen, setIsOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border/40 bg-surface/20 p-4">
        <div className="h-6 w-32 animate-pulse rounded bg-border/50" />
      </div>
    );
  }

  if (!chain || !chain.strikes?.length) return null;

  const spot = chain.spot;
  const strikes = chain.strikes;

  return (
    <div className="rounded-2xl border border-border/40 bg-surface/20 p-4 shadow-sm backdrop-blur-md transition-all duration-300">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between text-left text-sm font-medium text-primary transition-colors hover:text-accent"
      >
        <span className="flex items-center gap-2">📊 Live Options Chain <span className="rounded bg-surface/50 px-1.5 py-0.5 text-[10px] text-secondary">Spot: {spot.toFixed(2)}</span></span>
        <span className="text-xs text-secondary/60">{isOpen ? '▼' : '▶'}</span>
      </button>

      {isOpen && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/30 text-secondary/60">
                <th className="py-1.5 pr-2 text-left font-medium">Strike</th>
                <th className="py-1.5 pr-2 text-right font-medium text-profit/80">Call LTP</th>
                <th className="py-1.5 pr-2 text-right font-medium text-profit/80">Call OI</th>
                <th className="py-1.5 pr-2 text-right font-medium text-loss/80">Put LTP</th>
                <th className="py-1.5 pr-2 text-right font-medium text-loss/80">Put OI</th>
              </tr>
            </thead>
            <tbody>
              {strikes.map((s: any) => {
                const isATM = Math.abs(s.strike - spot) < (strikes.length > 1 ? Math.abs(strikes[1].strike - strikes[0].strike) : 50);
                return (
                  <tr key={s.strike} className={`border-b border-border/20 transition-colors hover:bg-surface/50 ${isATM ? 'bg-accent/5' : ''}`}>
                    <td className="py-1.5 pr-2 font-medium tabular-nums text-primary">
                      {s.strike}
                      {isATM && <span className="ml-1 text-[8px] font-bold text-accent">ATM</span>}
                    </td>
                    <td
                      className="cursor-pointer py-1.5 pr-2 text-right tabular-nums text-profit hover:bg-profit/10 hover:font-bold"
                      onClick={() => onStrikeSelect(s.strike, 'call')}
                      title="Click to add Call leg"
                    >{s.call?.ltp?.toFixed(2) ?? '—'}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums text-secondary/80">{s.call?.oi?.toLocaleString() ?? '—'}</td>
                    <td
                      className="cursor-pointer py-1.5 pr-2 text-right tabular-nums text-loss hover:bg-loss/10 hover:font-bold"
                      onClick={() => onStrikeSelect(s.strike, 'put')}
                      title="Click to add Put leg"
                    >{s.put?.ltp?.toFixed(2) ?? '—'}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums text-secondary/80">{s.put?.oi?.toLocaleString() ?? '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}