import axios from 'axios';
import type { 
  Leg, 
  StrategyType, 
  StrategyMetrics, 
  AssumptionResult, 
  StressTestResult, 
  DataMode, 
  AdjustmentSimulateResponse, 
  HealthEvent, 
  StrategyDNA, 
  TimeDecaySeries 
} from '../types/strategy';

// Environment variable prevents the localhost crash when deployed to Vercel/Netlify
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Suppress console errors for intentionally aborted requests (like rapid leg edits)
    if (axios.isCancel(error)) {
        return Promise.reject(error);
    }
    console.error('API error:', error.message);
    return Promise.resolve({ data: { error: true, message: error.message || 'Request failed' } });
  }
);

interface ErrorResult { error: true; message: string; }
function isErrorResult(data: unknown): data is ErrorResult {
  return Boolean(data) && typeof data === 'object' && (data as ErrorResult).error === true;
}

export const checkHealth = async () => {
  const { data } = await api.get('/health');
  return isErrorResult(data) ? null : data;
};

export const getOptionChain = async (symbol: string) => {
  const { data } = await api.get(`/option-chain/${symbol}`);
  return isErrorResult(data) ? null : data;
};

export const analyzeStrategy = async (legs: Leg[], strategyType: StrategyType, symbol: string) => {
  const { data } = await api.post('/strategy/analyze', { legs, strategy_type: strategyType, symbol });
  return isErrorResult(data) ? null : data;
};

export const getPayoff = async (legs: Leg[], symbol: string) => {
  const { data } = await api.post('/strategy/payoff', { legs, symbol });
  return isErrorResult(data) ? null : data;
};

export const checkAssumptions = async (legs: Leg[], strategyType: StrategyType, symbol: string) => {
  const { data } = await api.post('/strategy/assumptions', { legs, strategy_type: strategyType, symbol });
  return isErrorResult(data) ? null : data;
};

export const runStressTest = async (legs: Leg[], symbol: string) => {
  const { data } = await api.post('/strategy/stress-test', { legs, symbol });
  return isErrorResult(data) ? null : data;
};

export const saveStrategy = async (strategyId: string, legs: Leg[], metrics: StrategyMetrics, symbol: string, strategyType: StrategyType) => {
  const { data } = await api.post('/strategy/save', { strategy_id: strategyId, legs, metrics, symbol, strategy_type: strategyType });
  return isErrorResult(data) ? null : data;
};

export const simulateAdjustment = async (originalLegs: Leg[], adjustedLegs: Leg[], symbol: string) => {
  const { data } = await api.post('/adjustment/simulate', { original_legs: originalLegs, adjusted_legs: adjustedLegs, symbol });
  return isErrorResult(data) ? null : data;
};

// UPDATED: Now accepts an AbortSignal to cancel in-flight requests
export const getCopilotHint = async (request: object, signal?: AbortSignal) => {
  try {
    const { data } = await api.post('/copilot/hint', request, { signal });
    return isErrorResult(data) ? '' : (data?.hint ?? '');
  } catch (error) {
    if (axios.isCancel(error)) throw error; // Pass cancellation error up
    return '';
  }
};

export const getExplanation = async (request: object) => {
  const { data } = await api.post('/explain', request);
  return isErrorResult(data) ? '' : (data?.explanation ?? '');
};

export const getHealthHistory = async (strategyId: string) => {
  const { data } = await api.get(`/strategy/${strategyId}/history`);
  return isErrorResult(data) ? [] : (data?.history ?? []);
};

export const getStrategyDNA = async (strategyType: string) => {
  const { data } = await api.get(`/strategy/dna/${strategyType}`);
  return data?.dna ?? null;
};

export const getTimeDecay = async (legs: Leg[], strategyType: StrategyType, symbol: string) => {
  const { data } = await api.post('/strategy/time-decay', { legs, strategy_type: strategyType, symbol });
  return data?.series ?? null;
};

// NEW: Routes the AI Prompt generation through the Axios instance
export const getPromptToTrade = async (text: string) => {
  const { data } = await api.post('/api/prompt-to-trade', { text });
  return isErrorResult(data) ? { success: false, message: data.message } : data;
};