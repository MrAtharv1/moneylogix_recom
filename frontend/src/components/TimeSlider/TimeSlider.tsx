/**
 * TimeSlider — Visualise how a strategy evolves as time passes.
 * Shows payoff curve changing + theta erosion as slider moves.
 */
import { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { TimeDecaySeries, TimeDecaySnapshot } from '../../types/strategy';
import { formatINR } from '../../utils/formatters';

interface Props {
  series: TimeDecaySeries | null;
  isLoading: boolean;
}

export function TimeSlider({ series, isLoading }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (series) setActiveIndex(0);
  }, [series]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="h-4 bg-[#2d3148] rounded animate-pulse w-1/2" />
        <div className="h-48 bg-[#2d3148] rounded animate-pulse" />
      </div>
    );
  }

  if (!series || series.snapshots.length === 0) return null;

  const snapshot: TimeDecaySnapshot = series.snapshots[activeIndex];
  const thetaSign = snapshot.theta_eroded_since_entry >= 0 ? '+' : '';

  // 1. Bulletproof data filtering (rejects NaN and Infinity)
  const validData = snapshot.payoff_curve
    ? snapshot.payoff_curve
        .filter((p) => p && Number.isFinite(p.price) && Number.isFinite(p.pnl))
        .map((p) => [p.price, p.pnl])
    : [];

  // 2. Simplified, crash-proof chart options (No visualMap gradient)
  const chartOption = {
    backgroundColor: 'transparent',
    grid: { left: 55, right: 15, top: 15, bottom: 35 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      axisLine: { lineStyle: { color: '#2d3148' } },
      splitLine: { lineStyle: { color: '#2d3148', type: 'dashed' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8', fontSize: 10,
        formatter: (v: number) => `₹${(v / 1000).toFixed(0)}k`
      },
      axisLine: { lineStyle: { color: '#2d3148' } },
      splitLine: { lineStyle: { color: '#2d3148', type: 'dashed' } }
    },
    series: [{
      type: 'line',
      data: validData,
      smooth: false,
      lineStyle: { width: 2, color: '#3b82f6' }, // Solid blue line
      areaStyle: { color: '#3b82f6', opacity: 0.1 },
      symbol: 'none'
    }],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1d27',
      borderColor: '#2d3148',
      formatter: (params: any) =>
        `Price: ₹${params[0].value[0].toLocaleString('en-IN')}<br/>P&L: ${formatINR(params[0].value[1])}`
    }
  };

  return (
    <div className="space-y-4">
      {/* Slider */}
      <div>
        <div className="flex justify-between text-xs text-[#94a3b8] mb-2">
          {series.snapshots.map((s, i) => (
            <span
              key={i}
              className={`cursor-pointer transition-colors ${
                i === activeIndex ? 'text-[#3b82f6] font-semibold' : 'hover:text-[#e2e8f0]'
              }`}
              onClick={() => setActiveIndex(i)}
            >
              {s.label}
            </span>
          ))}
        </div>
        <input
          type="range"
          min={0}
          max={series.snapshots.length - 1}
          value={activeIndex}
          onChange={e => setActiveIndex(Number(e.target.value))}
          className="w-full accent-[#3b82f6]"
        />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <StatBox
          label="Theta Eroded"
          value={`${thetaSign}${formatINR(snapshot.theta_eroded_since_entry)}`}
          color={snapshot.theta_eroded_since_entry >= 0 ? '#22c55e' : '#ef4444'}
          sub={`${snapshot.days_remaining}d remaining`}
        />
        <StatBox
          label="Max Profit Now"
          value={formatINR(snapshot.max_profit)}
          color="#22c55e"
          sub={`was ${formatINR(series.entry_max_profit)}`}
        />
        <StatBox
          label="Daily Theta"
          value={formatINR(snapshot.net_theta_per_day)}
          color={snapshot.net_theta_per_day >= 0 ? '#22c55e' : '#ef4444'}
          sub="per day"
        />
      </div>

      {/* Payoff chart at this point in time */}
      {/* 3. notMerge={true} ensures clean state transitions */}
      {validData.length > 1 ? (
        <ReactECharts option={chartOption} style={{ height: 200 }} notMerge={true} />
      ) : (
        <div className="flex items-center justify-center h-[200px] border border-dashed border-[#2d3148] rounded-lg text-xs text-[#94a3b8]">
          Chart data unavailable for this timeframe
        </div>
      )}
    </div>
  );
}

function StatBox({
  label, value, color, sub
}: {
  label: string; value: string; color: string; sub: string;
}) {
  return (
    <div className="rounded-lg bg-[#0f1117] border border-[#2d3148] p-3">
      <p className="text-xs text-[#94a3b8] mb-1">{label}</p>
      <p className="text-sm font-semibold" style={{ color }}>{value}</p>
      <p className="text-xs text-[#94a3b8] mt-0.5">{sub}</p>
    </div>
  );
}