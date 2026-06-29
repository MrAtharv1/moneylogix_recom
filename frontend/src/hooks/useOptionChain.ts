/**
 * useOptionChain.ts — Fetches the option chain for a given symbol.
 * Used by leg builder strike/expiry pickers to source live strikes.
 */
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
      setChain(result);
    } else {
      setError('Failed to load option chain. Check if backend is running.');
    }
    setIsLoading(false);
  }, [symbol]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { chain, isLoading, error, refetch };
}
