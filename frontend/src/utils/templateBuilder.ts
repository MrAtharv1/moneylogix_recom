import type { Leg, StrategyType } from '../types/strategy';
import { v4 as uuidv4 } from 'uuid';

export function buildTemplateLegs(
  templateName: StrategyType,
  spot: number,
  realStrikes: number[],
  lotSize: number,
  expiry: string,
  quantity: number = 1
): Partial<Leg>[] {
  if (!realStrikes || realStrikes.length === 0) return [];

  const atm = realStrikes.reduce((prev, curr) => Math.abs(curr - spot) < Math.abs(prev - spot) ? curr : prev);
  const sorted = [...realStrikes].sort((a, b) => a - b);
  const atmIdx = sorted.indexOf(atm);

  const strikeAt = (offset: number) => sorted[Math.max(0, Math.min(sorted.length - 1, atmIdx + offset))] ?? atm;

  const leg = (strike: number, option_type: 'call' | 'put', side: 'buy' | 'sell'): Partial<Leg> => ({
    id: uuidv4(), symbol: 'NIFTY', strike, expiry, option_type, side, quantity, lot_size: lotSize, iv: 0.138,
  });

  const TEMPLATES: Record<string, Partial<Leg>[]> = {
    iron_condor: [leg(strikeAt(-2), 'put', 'buy'), leg(strikeAt(-1), 'put', 'sell'), leg(strikeAt(+1), 'call', 'sell'), leg(strikeAt(+2), 'call', 'buy')],
    long_straddle: [leg(atm, 'call', 'buy'), leg(atm, 'put', 'buy')],
    long_strangle: [leg(strikeAt(-2), 'put', 'buy'), leg(strikeAt(+2), 'call', 'buy')],
    bull_call_spread: [leg(atm, 'call', 'buy'), leg(strikeAt(+2), 'call', 'sell')],
    bull_put_spread: [leg(strikeAt(-1), 'put', 'sell'), leg(strikeAt(-2), 'put', 'buy')],
    bear_put_spread: [leg(atm, 'put', 'buy'), leg(strikeAt(-2), 'put', 'sell')],
    bear_call_spread: [leg(atm, 'call', 'sell'), leg(strikeAt(+2), 'call', 'buy')],
    covered_call: [leg(strikeAt(+1), 'call', 'sell')],
  };

  return TEMPLATES[templateName] ?? [];
}