/**
 * strategyLink.ts — Encode/decode strategy state to/from URL query strings.
 * Pure frontend — no backend needed.
 */
import type { Leg, StrategyType } from '../types/strategy';

const SEP = '~';   // leg separator
const FIELD = '_'; // field separator within a leg

/**
 * Encode legs + strategy metadata into a compact query string.
 * Format: ?s=NIFTY&t=iron_condor&l=19000C_B_1_50~19500C_S_1_50
 */
export function encodeStrategyToQueryString(
  legs: Leg[],
  strategyType: StrategyType,
  symbol: string
): string {
  if (legs.length === 0) return '';

  const encodedLegs = legs
    .map((leg) => {
      // Format: strike optionType side quantity lotSize expiry iv
      // Example: 19000C_B_1_50_2024-07-25_0.138
      const optType = leg.option_type === 'call' ? 'C' : 'P';
      const side = leg.side === 'buy' ? 'B' : 'S';
      return [
        leg.strike,
        optType,
        side,
        leg.quantity,
        leg.lot_size,
        leg.expiry,
        leg.iv.toFixed(3),
      ].join(FIELD);
    })
    .join(SEP);

  const params = new URLSearchParams();
  params.set('s', symbol);
  params.set('t', strategyType);
  params.set('l', encodedLegs);

  return `?${params.toString()}`;
}

/**
 * Decode query string back to strategy state.
 * Returns null if invalid or missing.
 */
export function decodeQueryStringToStrategy(
  search: string
): { legs: Leg[]; strategyType: StrategyType; symbol: string } | null {
  const params = new URLSearchParams(search);
  const encodedLegs = params.get('l');
  const strategyType = params.get('t') as StrategyType | null;
  const symbol = params.get('s');

  if (!encodedLegs || !strategyType || !symbol) return null;

  const legParts = encodedLegs.split(SEP);
  const legs: Leg[] = legParts.map((part, index) => {
    const [strike, optType, side, quantity, lotSize, expiry, iv] = part.split(FIELD);

    return {
      id: `shared-${index}-${Date.now()}`,
      symbol,
      strike: parseFloat(strike),
      option_type: optType === 'C' ? 'call' : 'put',
      side: side === 'B' ? 'buy' : 'sell',
      quantity: parseInt(quantity, 10),
      lot_size: parseInt(lotSize, 10),
      expiry: expiry || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      iv: parseFloat(iv) || 0.138,
    };
  });

  return { legs, strategyType, symbol };
}