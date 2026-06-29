/**
 * ScenarioHeatmap — 5×7 color-coded grid showing P&L under different market scenarios.
 * Color scale: deep green (large profit) → neutral → deep red (large loss)
 * Center cell = current conditions (should be ~₹0).
 */
import type { StressTestResult } from '../../types/strategy';
import { formatINR } from '../../utils/formatters';

interface Props {
  result: StressTestResult;
}

function cellStyle(value: number): { bg: string; text: string } {
  if (value > 5000) return { bg: '#166534', text: '#ffffff' };
  if (value > 2000) return { bg: '#16a34a', text: '#ffffff' };
  if (value > 0) return { bg: '#bbf7d0', text: '#166534' };
  if (value === 0) return { bg: '#1a1d27', text: '#e2e8f0' };
  if (value < -5000) return { bg: '#991b1b', text: '#ffffff' };
  if (value < -2000) return { bg: '#ef4444', text: '#ffffff' };
  return { bg: '#fecaca', text: '#991b1b' }; // value < 0
}

export function ScenarioHeatmap({ result }: Props) {
  const { matrix, price_shocks, iv_shocks, max_gain_scenario, max_loss_scenario } = result;

  const centerRow = Math.floor(iv_shocks.length / 2);
  const centerCol = Math.floor(price_shocks.length / 2);

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto">
        <table className="border-collapse w-full min-w-[560px]">
          <thead>
            <tr>
              <th className="p-1" />
              {price_shocks.map((shock, colIdx) => (
                <th key={colIdx} className="text-secondary text-xs font-normal p-1 text-center whitespace-nowrap">
                  {shock}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {iv_shocks.map((ivShock, rowIdx) => (
              <tr key={rowIdx}>
                <th className="text-secondary text-xs font-normal p-1 text-right whitespace-nowrap pr-2">
                  {ivShock}
                </th>
                {matrix[rowIdx].map((value, colIdx) => {
                  const { bg, text } = cellStyle(value);
                  const isCenter = rowIdx === centerRow && colIdx === centerCol;
                  return (
                    <td
                      key={colIdx}
                      title={`Underlying ${price_shocks[colIdx]}, IV ${ivShock} → P&L: ${formatINR(value)}`}
                      className={`text-center text-xs font-mono p-2 rounded-control ${
                        isCenter ? 'ring-2 ring-white ring-inset' : ''
                      }`}
                      style={{ backgroundColor: bg, color: text }}
                    >
                      {formatINR(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-4 text-sm">
        <span className="text-profit">Best case: {formatINR(max_gain_scenario)}</span>
        <span className="text-loss">Worst case: {formatINR(max_loss_scenario)}</span>
      </div>
    </div>
  );
}
