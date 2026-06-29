// Mirrors backend Pydantic models exactly as TypeScript interfaces.

// Enums
export type OptionType = "call" | "put";
export type Side = "buy" | "sell";
export type StrategyType =
  | "iron_condor" | "long_straddle" | "long_strangle"
  | "bull_call_spread" | "bull_put_spread" | "bear_put_spread"
  | "covered_call" | "custom";
export type DataModeType = "live" | "cached" | "snapshot" | "demo";

// Domain types
export interface Leg {
  id: string;
  symbol: string;
  strike: number;
  expiry: string;         // ISO date "2024-07-25"
  option_type: OptionType;
  side: Side;
  quantity: number;
  lot_size: number;
  iv: number;             // decimal: 0.138 = 13.8%
}

export interface Greeks {
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  price: number;
  pop: number;
}

export interface LegGreekContribution {
  leg_id: string;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
}

export interface PortfolioGreeks {
  net_delta: number;
  net_gamma: number;
  net_theta: number;
  net_vega: number;
  leg_contributions: LegGreekContribution[];
}

export interface RiskMetrics {
  max_profit: number;         // 999999999 = unlimited
  max_loss: number;           // -999999999 = unlimited loss
  breakevens: number[];
  probability_of_profit: number;
  margin_required: number;
}

export interface LiquidityInfo {
  score: number;
  label: string;
  spread_pct: number;
}

export interface PayoffPoint {
  price: number;
  pnl: number;
}

export interface StrategyMetrics {
  legs: Leg[];
  greeks_per_leg: Greeks[];
  portfolio_greeks: PortfolioGreeks;
  risk_metrics: RiskMetrics;
  liquidity: LiquidityInfo;
  payoff_curve: PayoffPoint[];
  iv_rank: number;
  expected_move_pct: number;
}

export interface AssumptionCheck {
  name: string;
  status: "valid" | "broken" | "warning";
  reason: string;
  icon: string;
}

export interface AssumptionResult {
  checks: AssumptionCheck[];
  valid_count: number;
  total_count: number;
  score_display: string;
}

export interface StressTestResult {
  matrix: number[][];
  price_shocks: string[];
  iv_shocks: string[];
  max_loss_scenario: number;
  max_gain_scenario: number;
  current_pnl: number;
}

export interface HealthDiff {
  iv: { from: number; to: number; change: number; label: string; direction: string } | null;
  price: { from: number; to: number; pct: number; label: string } | null;
  pnl: { from: number; to: number; change: number; label: string } | null;
  delta: { from: number; to: number; change: number; label: string } | null;
  has_changes: boolean;
  dte_warning: boolean;
}

export interface HealthEvent {
  diff: HealthDiff;
  explanation: string;
  data_mode: string;
  checked_at: string;
}

export interface DataMode {
  mode: DataModeType;
  timestamp: string | null;
}

// Request/Response
export interface AdjustmentComparison {
  delta_max_profit: number;
  delta_max_loss: number;
  delta_margin: number;
  delta_net_theta: number;
  max_profit_changed_by: string;
  max_loss_changed_by: string;
  margin_changed_by: string;
  summary: string;
}

export interface AdjustmentSimulateResponse {
  original: StrategyMetrics;
  adjusted: StrategyMetrics;
  comparison: AdjustmentComparison;
  data_mode: DataMode;
}
