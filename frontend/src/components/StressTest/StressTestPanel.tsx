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
    return <div className="text-secondary text-sm p-4">Add legs and run analysis to see stress test scenarios</div>;
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-secondary text-sm p-4">
        <span className="inline-block w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        Computing 35 market scenarios…
      </div>
    );
  }

  if (error) {
    return <div className="text-loss text-sm p-4">{error}</div>;
  }

  if (!result) {
    return <div className="text-secondary text-sm p-4">Run analysis to see stress test scenarios</div>;
  }

  return <ScenarioHeatmap result={result} />;
}