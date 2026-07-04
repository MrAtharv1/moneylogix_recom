import { v4 as uuidv4 } from 'uuid';
import type { Leg, StrategyType } from '../types/strategy';

const SEP = '~';
const FIELD = '_';

export function encodeStrategyToQueryString(legs: Leg[], strategyType: StrategyType, symbol: string): string {
  if (legs.length === 0) return '';
  const encoded = legs.map(leg => {
    const opt = leg.option_type === 'call' ? 'C' : 'P';
    const side = leg.side === 'buy' ? 'B' : 'S';
    return [leg.strike, opt, side, leg.quantity, leg.lot_size, leg.expiry, leg.iv.toFixed(3)].join(FIELD);
  }).join(SEP);
  const params = new URLSearchParams();
  params.set('s', symbol);
  params.set('t', strategyType);
  params.set('l', encoded);
  return `?${params.toString()}`;
}

export function decodeQueryStringToStrategy(search: string): { legs: Leg[]; strategyType: StrategyType; symbol: string } | null {
  const params = new URLSearchParams(search);
  const encoded = params.get('l');
  const strategyType = params.get('t') as StrategyType | null;
  const symbol = params.get('s');
  if (!encoded || !strategyType || !symbol) return null;

  const parts = encoded.split(SEP);
  const legs: Leg[] = parts.map((part, idx) => {
    const [strike, opt, side, quantity, lotSize, expiry, iv] = part.split(FIELD);
    return {
      id: uuidv4(),  // FIXED: unique ID per leg
      symbol,
      strike: parseFloat(strike),
      option_type: opt === 'C' ? 'call' : 'put',
      side: side === 'B' ? 'buy' : 'sell',
      quantity: parseInt(quantity, 10),
      lot_size: parseInt(lotSize, 10),
      expiry: expiry || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      iv: parseFloat(iv) || 0.138,
    };
  });
  return { legs, strategyType, symbol };
}