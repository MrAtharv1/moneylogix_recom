/**
 * StressTestPanel — Stress test tab content.
 */
import { useState, useEffect, useRef } from 'react';
import type { Leg, StressTestResult } from '../../types/strategy';
import { runStressTest } from '../../api/client';
import { ScenarioHeatmap } from './ScenarioHeatmap';

interface Props {
  legs: Leg[];
  symbol: string;
  isVisible: boolean;
}

export function StressTestPanel({ legs, symbol, isVisible }: Props) {
  const [result, setResult] = useState<StressTestResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cachedLegsRef = useRef<Leg[] | null>(null);

  const legsChanged = (a: Leg[] | null, b: Leg[]) => {
    if (!a) return true;
    if (a.length !== b.length) return true;
    return JSON.stringify(a) !== JSON.stringify(b);
  };

  useEffect(() => {
    if (!isVisible) return;
    if (legs.length === 0) return;
    if (result && !legsChanged(cachedLegsRef.current, legs)) return;

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    runStressTest(legs, symbol)
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setResult(data);
          cachedLegsRef.current = legs;
        } else {
          setError('Stress test failed. Make sure backend is running.');
        }
        setIsLoading(false);
      })
      .catch((err: any) => {
        if (cancelled) return;
        setError(err?.message || 'Stress test failed. Network error.');
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVisible, legs, symbol]);

  if (legs.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Add legs and run analysis to view stress test scenarios
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center gap-3 rounded-2xl border border-border/40 bg-surface/20 text-sm text-secondary/70 shadow-sm backdrop-blur-md">
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        Computing 35 market scenarios…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-40 items-center justify-center rounded-2xl border border-loss/20 bg-loss/5 text-sm text-loss">
        {error}
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex h-40 items-center justify-center rounded-2xl border border-dashed border-border/60 bg-surface/10 text-sm text-secondary/60">
        Run analysis to view stress test scenarios
      </div>
    );
  }

  return <ScenarioHeatmap result={result} />;
}