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
      <div className="flex flex-col gap-4">
        <div className="h-4 w-1/3 animate-pulse rounded bg-border/50" />
        <div className="h-48 w-full animate-pulse rounded-2xl bg-surface/20" />
      </div>
    );
  }

  if (!series || series.snapshots.length === 0) return null;

  const snapshot: TimeDecaySnapshot = series.snapshots[activeIndex];
  const thetaSign = snapshot.theta_eroded_since_entry >= 0 ? '+' : '';

  const validData = snapshot.payoff_curve
    ? snapshot.payoff_curve
        .filter((p) => p && Number.isFinite(p.price) && Number.isFinite(p.pnl))
        .map((p) => [p.price, p.pnl])
    : [];

  const chartOption = {
    backgroundColor: 'transparent',
    grid: { left: 55, right: 15, top: 15, bottom: 35 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#8b949e', fontSize: 10, fontFamily: 'ui-sans-serif, system-ui, sans-serif' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'solid' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#8b949e', fontSize: 10, fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        formatter: (v: number) => `₹${(v / 1000).toFixed(0)}k`
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'solid' } }
    },
    series: [{
      type: 'line',
      data: validData,
      smooth: true,
      lineStyle: { 
        width: 2, 
        color: '#4f8cff',
        shadowBlur: 12, // Glow effect
        shadowColor: 'rgba(79, 140, 255, 0.4)' // Glow effect
      },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(79, 140, 255, 0.15)' }, { offset: 1, color: 'rgba(79, 140, 255, 0.01)' }]
        }
      },
      symbol: 'none'
    }],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 24, 39, 0.85)',
      borderColor: 'rgba(255,255,255,0.1)',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: '#e5e7eb', fontSize: 12, fontFamily: 'ui-sans-serif, system-ui, sans-serif' },
      extraCssText: 'backdrop-filter: blur(8px); border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);',
      formatter: (params: any) =>
        `<div style="display:flex;flex-direction:column;gap:4px;">
          <span style="color:#9ca3af;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Price: ₹${params[0].value[0].toLocaleString('en-IN')}</span>
          <span style="font-weight:600;font-variant-numeric:tabular-nums;color:#e5e7eb">P&L: ${formatINR(params[0].value[1])}</span>
        </div>`
    }
  };

  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-border/40 bg-surface/20 p-5 shadow-sm backdrop-blur-md">
      <div className="flex flex-col gap-3">
        <div className="flex justify-between text-[11px] font-medium uppercase tracking-wider text-secondary/70">
          {series.snapshots.map((s, i) => (
            <span
              key={i}
              className={`cursor-pointer transition-colors ${
                i === activeIndex ? 'text-accent' : 'hover:text-primary'
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
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-border/50 accent-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatBox
          label="Theta Eroded"
          value={`${thetaSign}${formatINR(snapshot.theta_eroded_since_entry)}`}
          valueClass={snapshot.theta_eroded_since_entry >= 0 ? 'text-profit' : 'text-loss'}
          sub={`${snapshot.days_remaining}d remaining`}
        />
        <StatBox
          label="Max Profit Now"
          value={formatINR(snapshot.max_profit)}
          valueClass="text-profit"
          sub={`was ${formatINR(series.entry_max_profit)}`}
        />
        <StatBox
          label="Daily Theta"
          value={formatINR(snapshot.net_theta_per_day)}
          valueClass={snapshot.net_theta_per_day >= 0 ? 'text-profit' : 'text-loss'}
          sub="per day"
        />
      </div>

      {validData.length > 1 ? (
        <ReactECharts option={chartOption} style={{ height: 200 }} notMerge={true} />
      ) : (
        <div className="flex h-[200px] items-center justify-center rounded-xl border border-dashed border-border/60 bg-surface/10 text-xs text-secondary/60">
          Chart data unavailable for this timeframe
        </div>
      )}
    </div>
  );
}

function StatBox({
  label, value, valueClass, sub
}: {
  label: string; value: string; valueClass: string; sub: string;
}) {
  return (
    <div className="flex flex-col justify-center rounded-xl ring-1 ring-white/5 bg-surface/20 p-3 transition-colors hover:bg-white/5">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-secondary/70">{label}</p>
      <p className={`text-sm font-semibold tabular-nums tracking-tight ${valueClass}`}>{value}</p>
      <p className="mt-1 text-[10px] text-secondary/50">{sub}</p>
    </div>
  );
}