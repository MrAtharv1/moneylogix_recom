"""
models.py — All request/response models for MoneyLogix Strategy Builder.
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Dict

# --- Enums ---
class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"

class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"

class StrategyType(str, Enum):
    IRON_CONDOR = "iron_condor"
    LONG_STRADDLE = "long_straddle"
    LONG_STRANGLE = "long_strangle"
    BULL_CALL_SPREAD = "bull_call_spread"
    BULL_PUT_SPREAD = "bull_put_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    COVERED_CALL = "covered_call"
    CUSTOM = "custom"

class DataModeType(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    SNAPSHOT = "snapshot"
    DEMO = "demo"

# --- Core domain models ---
class Leg(BaseModel):
    id: str
    symbol: str = "NIFTY"
    strike: float
    expiry: str                    # ISO date: "2024-07-25"
    option_type: OptionType
    side: Side
    quantity: int = Field(ge=1, le=50)
    lot_size: int = Field(ge=1)
    iv: float = Field(ge=0)
    entry_price: Optional[float] = None   # <-- FIXED: added optional field

class Greeks(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float
    price: float
    pop: float

class LegGreekContribution(BaseModel):
    leg_id: str
    delta: float
    gamma: float
    theta: float
    vega: float

class PortfolioGreeks(BaseModel):
    net_delta: float
    net_gamma: float
    net_theta: float
    net_vega: float
    leg_contributions: List[LegGreekContribution]

class RiskMetrics(BaseModel):
    max_profit: float
    max_loss: float
    breakevens: List[float]
    probability_of_profit: float
    margin_required: float

class LiquidityInfo(BaseModel):
    score: float
    label: str
    spread_pct: float

class PayoffPoint(BaseModel):
    price: float
    pnl: float

class RiskScore(BaseModel):
    score: int
    tier: str
    color: str
    breakdown: Dict
    interpretation: str

class StrategyMetrics(BaseModel):
    legs: List[Leg]
    greeks_per_leg: List[Greeks]
    portfolio_greeks: PortfolioGreeks
    risk_metrics: RiskMetrics
    liquidity: LiquidityInfo
    payoff_curve: List[PayoffPoint]
    iv_rank: float = 0.0
    expected_move_pct: float = 0.0
    risk_score: Optional[RiskScore] = None

class AssumptionCheck(BaseModel):
    name: str
    status: str
    reason: str
    icon: str

class AssumptionResult(BaseModel):
    checks: List[AssumptionCheck]
    valid_count: int
    total_count: int
    score_display: str

class StressTestResult(BaseModel):
    matrix: List[List[float]]
    price_shocks: List[str]
    iv_shocks: List[str]
    max_loss_scenario: float
    max_gain_scenario: float
    current_pnl: float

class HealthDiff(BaseModel):
    iv: Optional[Dict] = None
    price: Optional[Dict] = None
    pnl: Optional[Dict] = None
    delta: Optional[Dict] = None
    has_changes: bool = False
    dte_warning: bool = False

class DataMode(BaseModel):
    mode: DataModeType
    timestamp: Optional[str] = None

# --- Request / Response ---
class AnalyzeRequest(BaseModel):
    legs: List[Leg]
    strategy_type: StrategyType = StrategyType.CUSTOM
    symbol: str = "NIFTY"

class AnalyzeResponse(BaseModel):
    metrics: StrategyMetrics
    assumptions: AssumptionResult
    data_mode: DataMode

class SaveStrategyRequest(BaseModel):
    strategy_id: str
    legs: List[Leg]
    metrics: StrategyMetrics
    symbol: str
    strategy_type: StrategyType

class AdjustmentSimulateRequest(BaseModel):
    original_legs: List[Leg]
    adjusted_legs: List[Leg]
    symbol: str = "NIFTY"

class AdjustmentComparison(BaseModel):
    delta_max_profit: float
    delta_max_loss: float
    delta_margin: float
    delta_net_theta: float
    max_profit_changed_by: str
    max_loss_changed_by: str
    margin_changed_by: str
    summary: str

class AdjustmentSimulateResponse(BaseModel):
    original: StrategyMetrics
    adjusted: StrategyMetrics
    comparison: AdjustmentComparison
    data_mode: DataMode

class CopilotHintRequest(BaseModel):
    changed_leg_before: Leg
    changed_leg_after: Leg
    metrics_before: StrategyMetrics
    metrics_after: StrategyMetrics

class HealthEvent(BaseModel):
    diff: HealthDiff
    explanation: str
    data_mode: str
    checked_at: str

class StrategyDNA(BaseModel):
    strategy_type: str
    display_name: str
    goal: str
    best_market: str
    worst_market: str
    time_sensitivity: str
    volatility_sensitivity: str
    max_risk_description: str
    max_reward_description: str
    key_risks: List[str]
    ideal_entry_conditions: List[str]