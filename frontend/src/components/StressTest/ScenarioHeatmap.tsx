/**
 * ScenarioHeatmap — 5×7 color-coded grid showing P&L under different market scenarios.
 * Refined premium color scale. Center cell = current conditions.
 */
import type { StressTestResult } from '../../types/strategy';
import { formatINR } from '../../utils/formatters';

interface Props {
  result: StressTestResult;
}

// Refined, enterprise-grade color mapping
function cellStyle(value: number): { bg: string; text: string; border: string } {
  if (value > 5000) return { bg: '#064e3b', text: '#34d399', border: 'border-[#065f46]' }; // Deep green
  if (value > 2000) return { bg: '#065f46', text: '#6ee7b7', border: 'border-[#047857]' };
  if (value > 0) return { bg: '#047857', text: '#a7f3d0', border: 'border-[#059669]' };
  if (value === 0) return { bg: 'rgba(255,255,255,0.03)', text: '#9ca3af', border: 'border-white/5' };
  if (value < -5000) return { bg: '#7f1d1d', text: '#fca5a5', border: 'border-[#991b1b]' }; // Deep red
  if (value < -2000) return { bg: '#991b1b', text: '#fecaca', border: 'border-[#b91c1c]' };
  return { bg: '#b91c1c', text: '#fee2e2', border: 'border-[#dc2626]' }; // value < 0
}

export function ScenarioHeatmap({ result }: Props) {
  const { matrix, price_shocks, iv_shocks, max_gain_scenario, max_loss_scenario } = result;

  const centerRow = Math.floor(iv_shocks.length / 2);
  const centerCol = Math.floor(price_shocks.length / 2);

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto rounded-2xl border border-border/40 bg-surface/20 p-4 shadow-sm backdrop-blur-md">
        <table className="w-full min-w-[560px] border-collapse">
          <thead>
            <tr>
              <th className="p-1" />
              {price_shocks.map((shock, colIdx) => (
                <th key={colIdx} className="p-2 text-center text-[10px] font-semibold uppercase tracking-wider text-secondary/70 whitespace-nowrap">
                  {shock}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-transparent gap-1">
            {iv_shocks.map((ivShock, rowIdx) => (
              <tr key={rowIdx}>
                <th className="pr-4 text-right text-[10px] font-semibold uppercase tracking-wider text-secondary/70 whitespace-nowrap align-middle">
                  {ivShock}
                </th>
                {matrix[rowIdx].map((value, colIdx) => {
                  const { bg, text, border } = cellStyle(value);
                  const isCenter = rowIdx === centerRow && colIdx === centerCol;
                  return (
                    <td key={colIdx} className="p-0.5">
                      <div
                        title={`Underlying ${price_shocks[colIdx]}, IV ${ivShock} → P&L: ${formatINR(value)}`}
                        className={`flex h-10 items-center justify-center rounded-lg border text-[11px] font-medium tabular-nums transition-transform hover:scale-[1.02] ${
                          isCenter ? 'ring-1 ring-accent ring-offset-1 ring-offset-background' : border
                        }`}
                        style={{ backgroundColor: bg, color: text }}
                      >
                        {formatINR(value)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-6 px-1 text-xs font-medium">
        <span className="flex items-center gap-1.5 text-secondary">
          Best case scenario: <span className="text-profit tabular-nums">{formatINR(max_gain_scenario)}</span>
        </span>
        <span className="flex items-center gap-1.5 text-secondary">
          Worst case scenario: <span className="text-loss tabular-nums">{formatINR(max_loss_scenario)}</span>
        </span>
      </div>
    </div>
  );
}