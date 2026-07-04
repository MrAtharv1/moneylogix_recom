const UNLIMITED_PROFIT = 999999999;
const UNLIMITED_LOSS = -999999999;

export const formatINR = (amount: number): string => {
  if (amount >= UNLIMITED_PROFIT) return "Unlimited";
  if (amount <= UNLIMITED_LOSS) return "Unlimited Loss";
  const abs = Math.abs(amount);
  const formatted = abs.toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,  // FIXED: now shows paise
  });
  return amount < 0 ? `-${formatted}` : formatted;
};

export const formatIV = (iv: number): string => `${(iv * 100).toFixed(1)}%`;
export const formatDelta = (delta: number): string => delta >= 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2);
export const formatPct = (value: number): string => `${(value * 100).toFixed(1)}%`;
export const getPnLClass = (pnl: number): string => pnl >= 0 ? "text-profit" : "text-loss";
export const formatPrice = (price: number): string => price.toLocaleString('en-IN', { maximumFractionDigits: 1 });
export const formatTheta = (theta: number): string => `${formatINR(theta)}/day`;