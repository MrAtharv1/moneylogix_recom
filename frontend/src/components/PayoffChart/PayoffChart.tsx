/**
 * PayoffChart — Interactive payoff diagram using Apache ECharts.
 * Shows strategy P&L at expiry across underlying price range.
 * Green above zero, red below. Vertical lines at breakevens.
 */
import ReactECharts from 'echarts-for-react';
import type { PayoffPoint } from '../../types/strategy';
import { formatINR, formatPrice } from '../../utils/formatters';

interface Props {
  curve: PayoffPoint[];
  breakevens: number[];
  maxProfit: number;
  maxLoss: number;
  height?: number;
  xAxisRange?: [number, number]; 
}

export function PayoffChart({ curve, breakevens, height = 300, xAxisRange }: Props) {
  if (!curve || curve.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Run analysis to view payoff chart
      </div>
    );
  }

  const minPrice = Math.min(...curve.map(p => p.price));
  const maxPrice = Math.max(...curve.map(p => p.price));
  const validBreakevens = breakevens.filter(be => be >= minPrice && be <= maxPrice);

  const breakevenLines = validBreakevens.map((be) => ({
    xAxis: be,
    label: {
      formatter: () => `BE ${formatPrice(be)}`,
      color: '#8b949e',
      fontSize: 10,
      fontFamily: 'ui-sans-serif, system-ui, sans-serif',
      padding: [0, 4],
    },
    lineStyle: { color: '#8b949e', type: 'dashed' as const, width: 1, opacity: 0.5 },
  }));

  const option: any = {
    backgroundColor: 'transparent',
    grid: { left: 60, right: 20, top: 20, bottom: 40 },

    xAxis: {
      type: 'value',
      min: xAxisRange ? xAxisRange[0] : undefined,
      max: xAxisRange ? xAxisRange[1] : undefined,
      axisLabel: {
        color: '#8b949e',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        formatter: (val: number) => formatPrice(val),
      },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'solid' } },
    },

    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#8b949e',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        formatter: (val: number) => formatINR(val),
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'solid' } },
    },

    series: [
      {
        type: 'line',
        data: curve.map((p) => [p.price, p.pnl]),
        smooth: true,
        lineStyle: { 
          width: 2, 
          color: '#4f8cff',
          shadowBlur: 12, // The Magic Glow Effect
          shadowColor: 'rgba(79, 140, 255, 0.4)' // The Magic Glow Effect
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(79, 140, 255, 0.15)' },
              { offset: 1, color: 'rgba(79, 140, 255, 0.01)' }
            ]
          }
        },
        symbol: 'none',
        markLine: {
          symbol: 'none',
          data: [{ yAxis: 0, lineStyle: { color: 'rgba(255,255,255,0.2)', type: 'solid', width: 1 } }, ...breakevenLines],
        },
      },
    ],

    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 24, 39, 0.85)',
      borderColor: 'rgba(255,255,255,0.1)',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: '#e5e7eb', fontSize: 12, fontFamily: 'ui-sans-serif, system-ui, sans-serif' },
      extraCssText: 'backdrop-filter: blur(8px); border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);',
      formatter: (params: any) => {
        const point = Array.isArray(params) ? params[0] : params;
        const [price, pnl] = point.value;
        const pnlColor = pnl >= 0 ? '#4ade80' : '#f87171'; 
        return `
          <div style="display:flex;flex-direction:column;gap:4px;">
            <span style="color:#9ca3af;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Price: ${formatPrice(price)}</span>
            <span style="font-weight:600;font-variant-numeric:tabular-nums;color:${pnlColor}">P&amp;L: ${formatINR(pnl)}</span>
          </div>
        `;
      },
    },
  };

  return <ReactECharts option={option} style={{ height }} notMerge={true} />;
}