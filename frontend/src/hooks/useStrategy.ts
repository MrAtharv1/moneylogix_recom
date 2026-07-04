import { useReducer, useCallback, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { analyzeStrategy, saveStrategy, getTimeDecay } from '../api/client';
import { decodeQueryStringToStrategy } from '../utils/strategyLink';
import type { Leg, StrategyType, StrategyMetrics, AssumptionResult, DataMode, TimeDecaySeries } from '../types/strategy';

interface StrategyState {
  legs: Leg[];
  strategyType: StrategyType;
  symbol: string;
  metrics: StrategyMetrics | null;
  assumptions: AssumptionResult | null;
  timeDecaySeries: TimeDecaySeries | null; // <--- ADDED
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
  | { type: 'SET_METRICS'; payload: { metrics: StrategyMetrics; assumptions: AssumptionResult; timeDecaySeries: TimeDecaySeries | null; mode: DataMode } } // <--- ADDED timeDecaySeries
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
  timeDecaySeries: null, // <--- ADDED
  isAnalyzing: false,
  isSaving: false,
  error: null,
  savedStrategyId: null,
  dataMode: null,
};

function reducer(state: StrategyState, action: Action): StrategyState {
  switch (action.type) {
    case 'ADD_LEG': return { ...state, legs: [...state.legs, action.payload] };
    case 'REMOVE_LEG': return { ...state, legs: state.legs.filter(l => l.id !== action.payload) };
    case 'UPDATE_LEG': return { ...state, legs: state.legs.map(l => l.id === action.payload.id ? { ...l, ...action.payload.updates } : l) };
    case 'SET_LEGS': return { ...state, legs: action.payload };
    case 'SET_STRATEGY_TYPE': return { ...state, strategyType: action.payload };
    case 'SET_SYMBOL': return { ...state, symbol: action.payload };
    case 'SET_METRICS': return { 
        ...state, 
        metrics: action.payload.metrics, 
        assumptions: action.payload.assumptions, 
        timeDecaySeries: action.payload.timeDecaySeries, // <--- ADDED
        dataMode: action.payload.mode, 
        error: null 
    };
    case 'SET_ANALYZING': return { ...state, isAnalyzing: action.payload };
    case 'SET_SAVING': return { ...state, isSaving: action.payload };
    case 'SET_ERROR': return { ...state, error: action.payload };
    case 'SET_SAVED_ID': return { ...state, savedStrategyId: action.payload };
    case 'RESET': return initialState;
    default: return state;
  }
}

export function useStrategy() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const autoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const shared = decodeQueryStringToStrategy(window.location.search);
    if (shared) {
      dispatch({ type: 'SET_SYMBOL', payload: shared.symbol });
      dispatch({ type: 'SET_STRATEGY_TYPE', payload: shared.strategyType });
      dispatch({ type: 'SET_LEGS', payload: shared.legs });
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const addLeg = useCallback((overrides: any = {}) => {
    const safe = overrides?.nativeEvent ? {} : overrides;
    dispatch({ type: 'ADD_LEG', payload: { ...DEFAULT_LEG, id: uuidv4(), ...safe } });
  }, []);

  const removeLeg = useCallback((id: string) => dispatch({ type: 'REMOVE_LEG', payload: id }), []);
  const updateLeg = useCallback((id: string, updates: Partial<Leg>) => dispatch({ type: 'UPDATE_LEG', payload: { id, updates } }), []);
  const setLegs = useCallback((legs: Leg[]) => dispatch({ type: 'SET_LEGS', payload: legs }), []);
  const setStrategyType = (t: StrategyType) => dispatch({ type: 'SET_STRATEGY_TYPE', payload: t });
  const setSymbol = (s: string) => dispatch({ type: 'SET_SYMBOL', payload: s });

  const analyzeNow = useCallback(async (legs = state.legs, strategyType = state.strategyType, symbol = state.symbol) => {
    if (legs.length === 0) return;
    dispatch({ type: 'SET_ANALYZING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });
    
    try {
      // Fetch both endpoints simultaneously so the slider and the chart load instantly together
      const [result, timeDecay] = await Promise.all([
        analyzeStrategy(legs, strategyType, symbol),
        getTimeDecay(legs, strategyType, symbol)
      ]);
      
      if (result) {
        dispatch({ 
          type: 'SET_METRICS', 
          payload: { 
            metrics: result.metrics, 
            assumptions: result.assumptions, 
            timeDecaySeries: timeDecay, // <--- Passes it down to the UI
            mode: result.data_mode 
          } 
        });
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'Analysis failed.' });
      }
    } catch (e: any) {
      dispatch({ type: 'SET_ERROR', payload: e?.message || 'Network error.' });
    } finally {
      dispatch({ type: 'SET_ANALYZING', payload: false });
    }
  }, [state.legs, state.strategyType, state.symbol]);

  const triggerAutoAnalyze = useCallback((legs = state.legs, strategyType = state.strategyType, symbol = state.symbol) => {
    if (legs.length === 0) return;
    if (autoTimer.current) clearTimeout(autoTimer.current);
    autoTimer.current = setTimeout(() => {
      analyzeNow(legs, strategyType, symbol);
    }, 500);
  }, [state.legs, state.strategyType, state.symbol, analyzeNow]);

  const saveCurrent = useCallback(async () => {
    if (!state.metrics) return null;
    const sid = uuidv4();
    dispatch({ type: 'SET_SAVING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });
    try {
      const result = await saveStrategy(sid, state.legs, state.metrics, state.symbol, state.strategyType);
      if (result?.saved) {
        const finalId = result.strategy_id || sid;
        dispatch({ type: 'SET_SAVED_ID', payload: finalId });
        return finalId;
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'Save failed.' });
      }
    } catch (e: any) {
      dispatch({ type: 'SET_ERROR', payload: e?.message || 'Save error.' });
    } finally {
      dispatch({ type: 'SET_SAVING', payload: false });
    }
    return null;
  }, [state.metrics, state.legs, state.symbol, state.strategyType]);

  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);

  return {
    state, addLeg, removeLeg, updateLeg, setLegs, analyzeNow, 
    triggerAutoAnalyze, saveCurrent, reset, setStrategyType, setSymbol,
  };
}