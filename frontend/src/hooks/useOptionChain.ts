import { useState, useEffect, useCallback } from 'react';
import { getOptionChain } from '../api/client';

export function useOptionChain(symbol: string) {
  const [chain, setChain] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!symbol) return;
    setIsLoading(true);
    setError(null);
    const result = await getOptionChain(symbol);
    if (result) {
      setChain(result.chain); // <-- FIX: extract the nested chain
    } else {
      setError('Failed to load option chain.');
    }
    setIsLoading(false);
  }, [symbol]);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    const fetchData = async () => {
      if (!symbol) return;
      setIsLoading(true);
      setError(null);
      try {
        const result = await getOptionChain(symbol);
        if (mounted && !controller.signal.aborted) {
          if (result) setChain(result.chain); // <-- FIX: extract the nested chain
          else setError('Failed to load option chain.');
        }
      } catch (e) {
        if (mounted && !controller.signal.aborted) setError('Network error.');
      } finally {
        if (mounted && !controller.signal.aborted) setIsLoading(false);
      }
    };
    fetchData();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [symbol]);

  return { chain, isLoading, error, refetch };
}