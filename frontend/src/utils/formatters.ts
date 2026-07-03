/**
 * formatters.ts — Consistent number formatting for Indian financial context.
 * Import these everywhere you display numbers — NEVER use raw numbers in JSX.
 */

const UNLIMITED_PROFIT = 999999999;
const UNLIMITED_LOSS = -999999999;

// Indian currency format: ₹1,00,000 (not ₹100,000)
export const formatINR = (amount: number): string => {
  if (amount >= UNLIMITED_PROFIT) return "Unlimited";
  if (amount <= UNLIMITED_LOSS) return "Unlimited Loss";
  const abs = Math.abs(amount);
  const formatted = abs.toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  });
  return amount < 0 ? `-${formatted}` : formatted;
};

// IV as percentage: 0.138 → "13.8%"
export const formatIV = (iv: number): string => `${(iv * 100).toFixed(1)}%`;

// Delta with sign: 0.5194 → "+0.52", -0.3 → "-0.30"
export const formatDelta = (delta: number): string =>
  delta >= 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2);

// Percentage: 0.72 → "72.0%"
export const formatPct = (value: number): string => `${(value * 100).toFixed(1)}%`;

// P&L with color indicator: positive → green class, negative → red class
export const getPnLClass = (pnl: number): string =>
  pnl >= 0 ? "text-profit" : "text-loss";

// Nifty price formatting: 19000.5 → "19,000.5"
export const formatPrice = (price: number): string =>
  price.toLocaleString('en-IN', { maximumFractionDigits: 1 });

// Greeks daily theta: -12.5 → "₹-12.50/day"
export const formatTheta = (theta: number): string =>
  `${formatINR(theta)}/day`;