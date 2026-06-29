/**
 * client.ts — Typed API functions for all backend endpoints.
 * All functions return typed results. All errors are caught and returned
 * as { error: true, message: string } — never throw to calling code.
 */
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
} from '../types/strategy';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 15000,
});

// Response interceptor: catch errors, return them as data (never throw)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API error:', error.message);
    return Promise.resolve({
      data: { error: true, message: error.message || 'Request failed' },
    });
  }
);

interface ErrorResult {
  error: true;
  message: string;
}

function isErrorResult(data: unknown): data is ErrorResult {
  return Boolean(data) && typeof data === 'object' && (data as ErrorResult).error === true;
}

// ---- Health check ----

export const checkHealth = async (): Promise<{ status: string } | null> => {
  const { data } = await api.get('/health');
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Option chain ----

export const getOptionChain = async (symbol: string): Promise<any | null> => {
  const { data } = await api.get(`/option-chain/${symbol}`);
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Analyze ----

export const analyzeStrategy = async (
  legs: Leg[],
  strategyType: StrategyType,
  symbol: string
): Promise<{ metrics: StrategyMetrics; assumptions: AssumptionResult; data_mode: DataMode } | null> => {
  const { data } = await api.post('/strategy/analyze', { legs, strategy_type: strategyType, symbol });
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Payoff ----

export const getPayoff = async (
  legs: Leg[],
  symbol: string
): Promise<{ payoff_curve: StrategyMetrics['payoff_curve']; risk_metrics: StrategyMetrics['risk_metrics']; data_mode: DataMode } | null> => {
  const { data } = await api.post('/strategy/payoff', { legs, symbol });
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Assumptions ----

export const checkAssumptions = async (
  legs: Leg[],
  strategyType: StrategyType,
  symbol: string
): Promise<{ assumptions: AssumptionResult; data_mode: DataMode } | null> => {
  const { data } = await api.post('/strategy/assumptions', { legs, strategy_type: strategyType, symbol });
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Stress test ----

export const runStressTest = async (
  legs: Leg[],
  symbol: string
): Promise<StressTestResult | null> => {
  const { data } = await api.post('/strategy/stress-test', { legs, symbol });
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Save ----

export const saveStrategy = async (
  strategyId: string,
  legs: Leg[],
  metrics: StrategyMetrics,
  symbol: string,
  strategyType: StrategyType
): Promise<{ saved: boolean; strategy_id?: string } | null> => {
  const { data } = await api.post('/strategy/save', {
    strategy_id: strategyId,
    legs,
    metrics,
    symbol,
    strategy_type: strategyType,
  });
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Adjustment simulation ----

export const simulateAdjustment = async (
  originalLegs: Leg[],
  adjustedLegs: Leg[],
  symbol: string
): Promise<AdjustmentSimulateResponse | null> => {
  const { data } = await api.post('/adjustment/simulate', {
    original_legs: originalLegs,
    adjusted_legs: adjustedLegs,
    symbol,
  });
  if (isErrorResult(data)) return null;
  return data;
};

// ---- Copilot hint ----

export const getCopilotHint = async (request: object): Promise<string> => {
  const { data } = await api.post('/copilot/hint', request);
  if (isErrorResult(data)) return '';
  return data?.hint ?? '';
};

// ---- AI explanation ----

export const getExplanation = async (request: object): Promise<string> => {
  const { data } = await api.post('/explain', request);
  if (isErrorResult(data)) return '';
  return data?.explanation ?? '';
};

// ---- Health monitor history ----

export const getHealthHistory = async (strategyId: string): Promise<HealthEvent[]> => {
  const { data } = await api.get(`/strategy/${strategyId}/health-history`);
  if (isErrorResult(data)) return [];
  return data?.history ?? [];
};
