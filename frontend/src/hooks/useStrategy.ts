/**
 * useStrategy.ts — Central state management for strategy construction.
 */
import { useReducer, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { analyzeStrategy, saveStrategy } from '../api/client';
import { decodeQueryStringToStrategy } from '../utils/strategyLink';
import type { Leg, StrategyType, StrategyMetrics, AssumptionResult, DataMode } from '../types/strategy';

interface StrategyState {
  legs: Leg[];
  strategyType: StrategyType;
  symbol: string;
  metrics: StrategyMetrics | null;
  assumptions: AssumptionResult | null;
  isAnalyzing: boolean;
  isSaving: boolean;
  error: string | null;
  savedStrategyId: string | null;
  dataMode: DataMode | null;
}

type Action =
  | { type: 'ADD_LEG'; payload: Leg }
  | { type: 'REMOVE_LEG'; payload: string }
  | { type: 'UPDATE_LEG'; payload: { id: string; updates: Partial<Leg> } }
  | { type: 'SET_LEGS'; payload: Leg[] }
  | { type: 'SET_STRATEGY_TYPE'; payload: StrategyType }
  | { type: 'SET_SYMBOL'; payload: string }
  | { type: 'SET_METRICS'; payload: { metrics: StrategyMetrics; assumptions: AssumptionResult; mode: DataMode } }
  | { type: 'SET_ANALYZING'; payload: boolean }
  | { type: 'SET_SAVING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_SAVED_ID'; payload: string }
  | { type: 'RESET' };

const DEFAULT_LEG: Omit<Leg, 'id'> = {
  symbol: 'NIFTY',
  strike: 19000,
  expiry: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  option_type: 'call',
  side: 'buy',
  quantity: 1,
  lot_size: 50,
  iv: 0.138,
};

const initialState: StrategyState = {
  legs: [],
  strategyType: 'custom',
  symbol: 'NIFTY',
  metrics: null,
  assumptions: null,
  isAnalyzing: false,
  isSaving: false,
  error: null,
  savedStrategyId: null,
  dataMode: null,
};

function reducer(state: StrategyState, action: Action): StrategyState {
  switch (action.type) {
    case 'ADD_LEG':
      return { ...state, legs: [...state.legs, action.payload] };
    case 'REMOVE_LEG':
      return { ...state, legs: state.legs.filter((leg) => leg.id !== action.payload) };
    case 'UPDATE_LEG':
      return {
        ...state,
        legs: state.legs.map((leg) =>
          leg.id === action.payload.id ? { ...leg, ...action.payload.updates } : leg
        ),
      };
    case 'SET_LEGS':
      return { ...state, legs: action.payload };
    case 'SET_STRATEGY_TYPE':
      return { ...state, strategyType: action.payload };
    case 'SET_SYMBOL':
      return { ...state, symbol: action.payload };
    case 'SET_METRICS':
      return {
        ...state,
        metrics: action.payload.metrics,
        assumptions: action.payload.assumptions,
        dataMode: action.payload.mode,
        error: null,
      };
    case 'SET_ANALYZING':
      return { ...state, isAnalyzing: action.payload };
    case 'SET_SAVING':
      return { ...state, isSaving: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_SAVED_ID':
      return { ...state, savedStrategyId: action.payload };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useStrategy() {
  const [state, dispatch] = useReducer(reducer, initialState);

  // ── URL SHARE: Read query string on mount ─────────────────────────────
  useEffect(() => {
    const shared = decodeQueryStringToStrategy(window.location.search);
    if (shared) {
      dispatch({ type: 'SET_SYMBOL', payload: shared.symbol });
      dispatch({ type: 'SET_STRATEGY_TYPE', payload: shared.strategyType });
      dispatch({ type: 'SET_LEGS', payload: shared.legs });
      // Clean the URL so it doesn't re-trigger on refresh
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);
  // ──────────────────────────────────────────────────────────────────────

  const addLeg = useCallback((overrides: any = {}) => {
    const safeOverrides = overrides?.nativeEvent ? {} : overrides;
    dispatch({
      type: 'ADD_LEG',
      payload: { ...DEFAULT_LEG, id: uuidv4(), ...safeOverrides },
    });
  }, []);

  const removeLeg = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_LEG', payload: id });
  }, []);

  const updateLeg = useCallback((id: string, updates: Partial<Leg>) => {
    dispatch({ type: 'UPDATE_LEG', payload: { id, updates } });
  }, []);

  const setLegs = useCallback((legs: Leg[]) => {
    dispatch({ type: 'SET_LEGS', payload: legs });
  }, []);

  const analyzeNow = useCallback(async (
    legs: Leg[] = state.legs,
    strategyType: StrategyType = state.strategyType,
    symbol: string = state.symbol
  ) => {
    if (legs.length === 0) return;

    dispatch({ type: 'SET_ANALYZING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      const result = await analyzeStrategy(legs, strategyType, symbol);
      if (result) {
        dispatch({
          type: 'SET_METRICS',
          payload: {
            metrics: result.metrics,
            assumptions: result.assumptions,
            mode: result.data_mode,
          },
        });
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'Analysis failed.' });
      }
    } catch (e: any) {
      dispatch({ type: 'SET_ERROR', payload: e?.message || 'Network error. Is backend running?' });
    } finally {
      dispatch({ type: 'SET_ANALYZING', payload: false });
    }
  }, [state.legs, state.strategyType, state.symbol]);

  const saveCurrent = useCallback(async (): Promise<string | null> => {
    if (!state.metrics) return null;
    
    const strategyId = uuidv4();
    dispatch({ type: 'SET_SAVING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });
    
    try {
      const result = await saveStrategy(strategyId, state.legs, state.metrics, state.symbol, state.strategyType);
      if (result?.saved) {
        const finalId = result.strategy_id || strategyId;
        dispatch({ type: 'SET_SAVED_ID', payload: finalId });
        return finalId;
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'Save failed.' });
      }
    } catch (e: any) {
      dispatch({ type: 'SET_ERROR', payload: e?.message || 'Network error during save.' });
    } finally {
      dispatch({ type: 'SET_SAVING', payload: false });
    }
    return null;
  }, [state.metrics, state.legs, state.symbol, state.strategyType]);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);
  
  return {
    state,
    addLeg,
    removeLeg,
    updateLeg,
    setLegs,
    analyzeNow,
    saveCurrent,
    reset,
    setStrategyType: (t: StrategyType) => dispatch({ type: 'SET_STRATEGY_TYPE', payload: t }),
    setSymbol: (s: string) => dispatch({ type: 'SET_SYMBOL', payload: s }),
  };
}