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
  xAxisRange?: [number, number]; // explicit domain override, used for side-by-side comparisons
}

export function PayoffChart({ curve, breakevens, height = 300, xAxisRange }: Props) {
  if (!curve || curve.length === 0) {
    return (
      <div className="flex items-center justify-center h-[300px] text-secondary text-sm">
        Run analysis to see payoff chart
      </div>
    );
  }

  // 1. Find the boundaries of the chart
  const minPrice = Math.min(...curve.map(p => p.price));
  const maxPrice = Math.max(...curve.map(p => p.price));

  // 2. Only draw breakevens that actually fit on the screen
  const validBreakevens = breakevens.filter(be => be >= minPrice && be <= maxPrice);

  const breakevenLines = validBreakevens.map((be) => ({
    xAxis: be,
    label: {
      formatter: () => `BE ${formatPrice(be)}`,
      color: '#94a3b8',
      fontSize: 10,
    },
    lineStyle: { color: '#94a3b8', type: 'dashed' as const, width: 1 },
  }));

  // Replace the 'const option: any = {' block entirely with this:
  const option: any = {
    backgroundColor: 'transparent',
    grid: { left: 60, right: 20, top: 20, bottom: 40 },

    xAxis: {
      type: 'value',
      min: xAxisRange ? xAxisRange[0] : undefined,
      max: xAxisRange ? xAxisRange[1] : undefined,
      axisLabel: {
        color: '#94a3b8',
        formatter: (val: number) => formatPrice(val),
      },
      axisLine: { lineStyle: { color: '#2d3148' } },
      splitLine: { lineStyle: { color: '#2d3148', type: 'dashed' } },
    },

    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8',
        formatter: (val: number) => formatINR(val),
      },
      axisLine: { lineStyle: { color: '#2d3148' } },
      splitLine: { lineStyle: { color: '#2d3148', type: 'dashed' } },
    },

    series: [
      {
        type: 'line',
        data: curve.map((p) => [p.price, p.pnl]),
        smooth: true, // Smooth lines render much safer in ECharts
        lineStyle: { width: 3, color: '#3b82f6' }, // Solid Accent Blue
        areaStyle: { color: '#3b82f6', opacity: 0.1 },
        symbol: 'none',
        markLine: {
          symbol: 'none',
          data: [{ yAxis: 0, lineStyle: { color: '#94a3b8', type: 'solid', width: 1 } }, ...breakevenLines],
        },
      },
    ],

    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1d27',
      borderColor: '#2d3148',
      textStyle: { color: '#e2e8f0' },
      formatter: (params: any) => {
        const point = Array.isArray(params) ? params[0] : params;
        const [price, pnl] = point.value;
        const pnlColor = pnl >= 0 ? '#22c55e' : '#ef4444';
        return `Price: ${formatPrice(price)}<br/>P&amp;L: <span style="color:${pnlColor};font-weight:bold">${formatINR(pnl)}</span>`;
      },
    },
  };

  // Add notMerge={true} to the return statement to prevent React/ECharts ghosting bugs
  return <ReactECharts option={option} style={{ height }} notMerge={true} />;
}

