"""
main.py — FastAPI application entry point for MoneyLogix Strategy Builder.

Run with: uvicorn main:app --reload --port 8000

Architecture overview:
  ┌─────────────────────────────────────────────────────────┐
  │  React Frontend (port 5173)                             │
  │    ↓ REST calls (strategy analysis, copilot hints)      │
  │    ↓ WebSocket (real-time health monitoring)            │
  ├─────────────────────────────────────────────────────────┤
  │  FastAPI (this file)                                    │
  │    ↓ quant engine (blackscholes, portfolio_greeks, ...)  │
  │    ↓ data layer (option chain with 4-tier fallback)     │
  │    ↓ AI layer (explainer + copilot, pluggable provider) │
  │    ↓ persistence (SQLite snapshots + health history)    │
  └─────────────────────────────────────────────────────────┘

4-tier data fallback (handled in data/fallback.py):
  1. Live NSE data feed
  2. Redis/in-memory cache (< 5 min stale)
  3. Saved snapshot from SQLite
  4. Mock data (always succeeds)

AI provider toggle (config.py / .env):
  AI_PROVIDER=mock   → no API calls, template responses, no key needed
  AI_PROVIDER=claude → calls Anthropic API, falls back to mock on failure
  AI_PROVIDER=huggingface → calls HuggingFace Inference API
"""

"""
main.py — FastAPI application entry point for MoneyLogix Strategy Builder.

Run with: uvicorn main:app --reload --port 8000
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import settings
from database import create_tables
from utils.logger import setup_logging
from utils.validators import validate_legs, validate_symbol

from engine.ai_prompt_router import router as ai_router
from data.fallback import get_option_chain
from engine import strategy_builder, assumption_checker, health_monitor
from engine import adjustment_simulator, snapshot
from quant.blackscholes import compute as bs_compute

from ai.explainer import explain_health_change
from ai.copilot import get_leg_hint

from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    SaveStrategyRequest,
    AdjustmentSimulateRequest,
    AdjustmentSimulateResponse,
    DataMode,
)

# ─── LOGGING SETUP ───────────────────────────────────────────────────────────
setup_logging(
    level=getattr(settings, "LOG_LEVEL", "INFO"),
    log_format=getattr(settings, "LOG_FORMAT", "text"),
)
logger = logging.getLogger(__name__)

# ─── STRATEGY DNA MAP ────────────────────────────────────────────────────────
STRATEGY_DNA_MAP = {
    "iron_condor": {
        "strategy_type": "iron_condor",
        "display_name": "Iron Condor",
        "goal": "Collect premium by selling options on both sides, profiting when the underlying stays within a range",
        "best_market": "Sideways market with high implied volatility",
        "worst_market": "Strong directional move in either direction",
        "time_sensitivity": "High — time decay (theta) works in your favour every day",
        "volatility_sensitivity": "High — built for high IV environments; IV crush benefits this strategy",
        "max_risk_description": "Limited to the width of the wider spread minus total premium received",
        "max_reward_description": "Total net premium collected at entry — realised if both short options expire worthless",
        "key_risks": ["Strong breakout beyond short strikes", "IV spike expanding short premiums", "Gap opening on news/event"],
        "ideal_entry_conditions": ["IV Rank above 60", "Sideways trend confirmed", "15+ days to expiry", "Adequate liquidity at all four strikes"]
    },
    "long_straddle": {
        "strategy_type": "long_straddle",
        "display_name": "Long Straddle",
        "goal": "Profit from a large move in either direction by buying both a call and put at the same strike",
        "best_market": "High uncertainty — any large move (earnings, RBI announcement, budget)",
        "worst_market": "Sideways market where the underlying goes nowhere",
        "time_sensitivity": "High — time decay (theta) works against you every day you hold",
        "volatility_sensitivity": "High — benefits from IV expansion; hurt by IV crush after the event",
        "max_risk_description": "Limited to total premium paid for both call and put",
        "max_reward_description": "Theoretically unlimited on the call side; substantial on the put side",
        "key_risks": ["IV crush after the anticipated event", "Underlying stays range-bound", "Time decay eroding value"],
        "ideal_entry_conditions": ["IV Rank below 40", "Known catalyst event upcoming", "7+ days to expiry"]
    },
    "bull_call_spread": {
        "strategy_type": "bull_call_spread",
        "display_name": "Bull Call Spread",
        "goal": "Profit from moderate upside in the underlying while limiting both cost and risk",
        "best_market": "Moderately bullish — expecting upside but not a runaway rally",
        "worst_market": "Bearish or sideways — loses the net debit paid if underlying stays flat",
        "time_sensitivity": "Moderate — time decay slightly works against you on the long leg",
        "volatility_sensitivity": "Low to moderate — less sensitive to IV than outright long calls",
        "max_risk_description": "Limited to net debit paid (buy price minus sell price of the spread)",
        "max_reward_description": "Limited to spread width minus net debit — realised if underlying closes above upper strike at expiry",
        "key_risks": ["Underlying fails to move up enough by expiry", "Sharp bearish reversal", "Time decay on long leg"],
        "ideal_entry_conditions": ["Bullish trend confirmed", "7+ days to expiry", "Reasonable IV levels"]
    },
    "long_strangle": {
        "strategy_type": "long_strangle",
        "display_name": "Long Strangle",
        "goal": "Profit from a large move in either direction using OTM options for lower cost than a straddle",
        "best_market": "High uncertainty with potential for large move — cheaper than straddle",
        "worst_market": "Sideways market with no significant move",
        "time_sensitivity": "High — theta decay accelerates near expiry",
        "volatility_sensitivity": "High — needs IV expansion or large underlying move",
        "max_risk_description": "Limited to total premium paid for both OTM call and put",
        "max_reward_description": "Theoretically unlimited on upside; substantial on downside",
        "key_risks": ["Underlying stays between the two strikes", "IV crush", "Accelerating time decay"],
        "ideal_entry_conditions": ["IV Rank below 40", "Known catalyst event upcoming", "10+ days to expiry"]
    },
    "bull_put_spread": {
        "strategy_type": "bull_put_spread",
        "display_name": "Bull Put Spread",
        "goal": "Collect premium by selling a put spread, profiting when the underlying stays above the short put strike",
        "best_market": "Bullish to neutral — underlying holding above support",
        "worst_market": "Sharp bearish move below the short put strike",
        "time_sensitivity": "High — theta works in your favour as a premium seller",
        "volatility_sensitivity": "Moderate — benefits from high IV at entry (sell expensive puts)",
        "max_risk_description": "Limited to spread width minus premium received",
        "max_reward_description": "Net premium received at entry — realised if underlying closes above short put at expiry",
        "key_risks": ["Sharp bearish breakdown", "IV spike expanding the spread value", "Gap down on news"],
        "ideal_entry_conditions": ["Bullish trend", "IV Rank above 50", "7+ days to expiry", "Clear support level above short strike"]
    },
    "bear_put_spread": {
        "strategy_type": "bear_put_spread",
        "display_name": "Bear Put Spread",
        "goal": "Profit from moderate downside in the underlying while limiting cost and risk",
        "best_market": "Moderately bearish — expecting decline but not a crash",
        "worst_market": "Bullish or sideways — loses the net debit if underlying stays flat or rises",
        "time_sensitivity": "Moderate — time decay slightly works against you",
        "volatility_sensitivity": "Low to moderate — less sensitive than outright long puts",
        "max_risk_description": "Limited to net debit paid",
        "max_reward_description": "Limited to spread width minus net debit — realised if underlying closes below lower strike",
        "key_risks": ["Underlying fails to move down", "Bullish reversal", "Time decay on long put"],
        "ideal_entry_conditions": ["Bearish trend confirmed", "7+ days to expiry", "Clear resistance above entry"]
    },
    "covered_call": {
        "strategy_type": "covered_call",
        "display_name": "Covered Call",
        "goal": "Generate income by selling a call against an existing long stock/futures position",
        "best_market": "Neutral to mildly bullish — stock expected to stay below call strike",
        "worst_market": "Strong rally above the call strike — caps your upside profit",
        "time_sensitivity": "High — theta decay on the short call benefits you as seller",
        "volatility_sensitivity": "Moderate — high IV is good at entry (sell expensive calls); IV drop after helps",
        "max_risk_description": "Effectively the cost of the underlying position minus premium received",
        "max_reward_description": "Premium received plus any gain up to the call strike price",
        "key_risks": ["Sharp rally above strike (unlimited opportunity cost)", "Sharp decline in underlying", "Early assignment risk on American options"],
        "ideal_entry_conditions": ["Already hold underlying position", "IV Rank above 50", "Neutral to mildly bullish outlook", "15+ days to expiry"]
    },
    "custom": {
        "strategy_type": "custom",
        "display_name": "Custom Strategy",
        "goal": "User-defined multi-leg strategy",
        "best_market": "Depends on leg configuration",
        "worst_market": "Depends on leg configuration",
        "time_sensitivity": "See theta in Greeks panel",
        "volatility_sensitivity": "See vega in Greeks panel",
        "max_risk_description": "See Max Loss in metrics panel",
        "max_reward_description": "See Max Profit in metrics panel",
        "key_risks": ["Depends on specific leg structure"],
        "ideal_entry_conditions": ["Defined by user strategy"]
    }
}

# ─── FASTAPI SETUP ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup. Creates DB tables (async) and logs config."""
    await create_tables()
    # Initialize AI Provider Singleton early
    from ai.base_provider import init_provider
    init_provider()
    logger.info(
        f"MoneyLogix Strategy Builder started | "
        f"AI provider: {settings.AI_PROVIDER} | "
        f"Environment: {getattr(settings, 'ENV', 'development')}"
    )
    yield

app = FastAPI(
    title="MoneyLogix Strategy Builder",
    description="SEBI-compliant options strategy lifecycle platform for Indian index options.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- Change this from settings.CORS_ORIGINS to ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)

# ─── MIDDLEWARE & EXCEPTION HANDLERS ─────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now(timezone.utc)
    response = await call_next(request)
    response_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"response_ms={response_ms:.0f}"
    )
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc}")
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": str(exc)})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

# ─── INTERNAL HELPERS ────────────────────────────────────────────────────────
def _enrich_legs_with_entry_price(legs: list[dict], chain: dict) -> list[dict]:
    spot = chain.get("spot", 19000)
    iv = chain.get("current_iv", 0.15)
    dte = chain.get("days_to_expiry", 30)
    r = 0.065
    enriched = []
    for leg in legs:
        leg_copy = dict(leg)
        if leg_copy.get("entry_price") is None:
            greeks = bs_compute(S=spot, K=leg["strike"], T_days=dte, r=r, sigma=iv, option_type=leg["option_type"])
            leg_copy["entry_price"] = greeks["price"]
        enriched.append(leg_copy)
    return enriched

def _build_market_state(metrics: dict, chain: dict, mode: str) -> dict:
    greeks = metrics.get("portfolio_greeks", {})
    risk = metrics.get("risk_metrics", {})
    liq_info = metrics.get("liquidity", {})
    iv_rank_val = metrics.get("iv_rank", 50.0)
    return {
        "spot_price": chain.get("spot", 0),
        "iv": chain.get("current_iv", 0),
        "iv_rank": iv_rank_val,
        "trend": "sideways",
        "expected_move": metrics.get("expected_move_pct", 0),
        "days_to_expiry": chain.get("days_to_expiry", 30),
        "liquidity_score": liq_info.get("score", 75.0),
        "net_delta": greeks.get("net_delta", 0),
        "net_theta": greeks.get("net_theta", 0),
        "max_profit": risk.get("max_profit", 0),
        "max_loss": risk.get("max_loss", 0),
        "data_mode": mode,
    }

# ─── API ROUTES ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health_check():
    return {
        "status": "ok", 
        "timestamp": datetime.now(timezone.utc).isoformat(), 
        "ai_provider": settings.AI_PROVIDER, 
        "version": "1.0.0"
    }

@app.get("/strategy/dna/{strategy_type}", tags=["strategy"])
async def get_strategy_dna(strategy_type: str):
    return {"dna": STRATEGY_DNA_MAP.get(strategy_type)}

@app.post("/strategy/time-decay", tags=["strategy"])
async def get_time_decay(request: AnalyzeRequest):
    try:
        chain, mode = await get_option_chain(request.symbol)
        spot, dte, current_iv = chain["spot"], chain["days_to_expiry"], chain["current_iv"]
        legs_dicts = [json.loads(leg.json()) for leg in request.legs]
        
        # FIX: Enrich the legs with entry_price so the Time Slider PnL exactly matches the Payoff Chart PnL
        legs_enriched = _enrich_legs_with_entry_price(legs_dicts, chain)
        
        series = strategy_builder.compute_time_decay_series(legs_enriched, spot, current_iv, dte)
        return {"series": series, "data_mode": mode}
    except Exception as e:
        logger.exception(f"Time decay computation failed: {e}")
        return {"series": {"snapshots": [], "entry_max_profit": 0, "entry_max_loss": 0}, "data_mode": "demo"}

@app.get("/option-chain/{symbol}", tags=["market-data"])
async def get_chain(symbol: str):
    errors = validate_symbol(symbol.upper())
    if errors: raise HTTPException(status_code=400, detail={"errors": errors})
    chain, mode = await get_option_chain(symbol.upper())
    return {"chain": chain, "data_mode": DataMode(mode=mode, timestamp=datetime.now(timezone.utc).isoformat())}

@app.post("/strategy/analyze", response_model=AnalyzeResponse, tags=["strategy"])
async def analyze_strategy(request: AnalyzeRequest):
    start_time = datetime.now(timezone.utc)
    legs_as_dicts = [json.loads(leg.json()) for leg in request.legs]
    errors = validate_legs(legs_as_dicts)
    if errors: raise HTTPException(status_code=400, detail={"errors": errors})

    # FIX: Await the new async strategy_builder
    metrics, mode = await strategy_builder.build_strategy_metrics(legs=legs_as_dicts, symbol=request.symbol.upper())
    
    chain, _ = await get_option_chain(request.symbol.upper())
    market_state = _build_market_state(metrics, chain, mode)
    assumptions = assumption_checker.check_assumptions(strategy_type=request.strategy_type, market_state=market_state)

    response_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    logger.info(f"Strategy analyzed | response_ms={response_ms:.0f}")

    return AnalyzeResponse(metrics=metrics, assumptions=assumptions, data_mode=DataMode(mode=mode, timestamp=datetime.now(timezone.utc).isoformat()))

@app.post("/strategy/payoff", tags=["strategy"])
async def strategy_payoff(request: dict):
    legs, symbol, num_points = request.get("legs", []), request.get("symbol", "NIFTY").upper(), request.get("num_points", 100)
    errors = validate_legs(legs) + validate_symbol(symbol)
    if errors: raise HTTPException(status_code=400, detail={"errors": errors})

    chain, mode = await get_option_chain(symbol)
    spot = chain.get("spot", 19000)
    legs = _enrich_legs_with_entry_price(legs, chain)

    from quant.payoff import compute_payoff_curve, find_breakevens, compute_max_profit_loss
    curve = compute_payoff_curve(legs, spot, num_points=num_points)
    breakevens = find_breakevens(curve)
    
    # Pass 'legs' down for analytic evaluation (unlimited risk fix)
    risk = compute_max_profit_loss(curve, legs=legs)

    return {
        "payoff_curve": curve,
        "risk_metrics": {"breakevens": breakevens, "max_profit": risk.get("max_profit", 0), "max_loss": risk.get("max_loss", 0)},
        "data_mode": DataMode(mode=mode, timestamp=datetime.now(timezone.utc).isoformat()),
    }

@app.post("/strategy/assumptions", tags=["strategy"])
async def check_strategy_assumptions(request: dict):
    legs, strategy_type, symbol = request.get("legs", []), request.get("strategy_type", "custom"), request.get("symbol", "NIFTY").upper()
    errors = validate_legs(legs) + validate_symbol(symbol)
    if errors: raise HTTPException(status_code=400, detail={"errors": errors})

    chain, mode = await get_option_chain(symbol)
    legs = _enrich_legs_with_entry_price(legs, chain)
    
    # FIX: Await the new async strategy_builder
    metrics, _ = await strategy_builder.build_strategy_metrics(legs=legs, symbol=symbol)
    market_state = _build_market_state(metrics, chain, mode)
    
    return {
        "assumptions": assumption_checker.check_assumptions(strategy_type, market_state),
        "data_mode": DataMode(mode=mode, timestamp=datetime.now(timezone.utc).isoformat()),
    }

@app.post("/strategy/stress-test", tags=["strategy"])
async def stress_test(request: dict):
    legs, symbol = request.get("legs", []), request.get("symbol", "NIFTY").upper()
    errors = validate_legs(legs) + validate_symbol(symbol)
    if errors: raise HTTPException(status_code=400, detail={"errors": errors})

    chain, mode = await get_option_chain(symbol)
    legs = _enrich_legs_with_entry_price(legs, chain)
    
    from quant.stress_test import run_stress_matrix
    stress_result = run_stress_matrix(
        legs=legs, 
        spot=chain.get("spot", 19000), 
        current_iv=chain.get("current_iv", 0.15), 
        T_days=chain.get("days_to_expiry", 30)
    )

    return {**stress_result, "data_mode": DataMode(mode=mode, timestamp=datetime.now(timezone.utc).isoformat())}

@app.post("/strategy/save", tags=["strategy"])
async def save_strategy(request: SaveStrategyRequest):
    legs_as_dicts = [json.loads(leg.json()) for leg in request.legs]
    errors = validate_legs(legs_as_dicts)
    if errors: raise HTTPException(status_code=400, detail={"errors": errors})

    # FIX: Await the new async strategy_builder
    metrics, mode = await strategy_builder.build_strategy_metrics(legs=legs_as_dicts, symbol=request.symbol.upper())
    
    chain, _ = await get_option_chain(request.symbol.upper())
    spot, iv = chain.get("spot", 19000), chain.get("current_iv", 0.15)
    legs_for_snapshot = metrics.get("legs") or legs_as_dicts

    strategy_id = await snapshot.create_strategy_snapshot(
        symbol=request.symbol.upper(), strategy_type=request.strategy_type,
        legs=legs_for_snapshot, metrics=metrics, spot=spot, iv=iv, chain=chain
    )
    return {"strategy_id": strategy_id, "saved": True}

@app.get("/strategy/{strategy_id}/history", tags=["strategy"])
async def get_strategy_history(strategy_id: str):
    # Await the async access mechanism
    history = await snapshot.get_health_history(strategy_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"strategy_id": strategy_id, "history": history}

@app.post("/adjustment/simulate", response_model=AdjustmentSimulateResponse, tags=["adjustments"])
async def simulate_adjustment_route(request: AdjustmentSimulateRequest):
    orig_legs = [json.loads(leg.json()) for leg in request.original_legs]
    adj_legs = [json.loads(leg.json()) for leg in request.adjusted_legs]
    
    # If adjustment_simulator calls get_option_chain internally, we await it here
    # (Assumes adjustment_simulator.simulate_adjustment is async if it makes network calls)
    if asyncio.iscoroutinefunction(adjustment_simulator.simulate_adjustment):
        result = await adjustment_simulator.simulate_adjustment(original_legs=orig_legs, adjusted_legs=adj_legs, symbol=request.symbol.upper())
    else:
        # Fallback if you haven't refactored simulator to be async internally yet
        result = adjustment_simulator.simulate_adjustment(original_legs=orig_legs, adjusted_legs=adj_legs, symbol=request.symbol.upper())
        
    mode_str = result.pop("data_mode", "demo")
    result["data_mode"] = {"mode": mode_str, "timestamp": datetime.now(timezone.utc).isoformat()}
    return AdjustmentSimulateResponse(**result)

# ─── ASYNC AI ROUTES ─────────────────────────────────────────────────────────
@app.post("/copilot/hint", tags=["ai"])
async def copilot_hint(request: dict):
    try:
        hint = await get_leg_hint(
            leg_before=request.get("changed_leg_before", {}),
            leg_after=request.get("changed_leg_after", {}),
            metrics_before=request.get("metrics_before", {}),
            metrics_after=request.get("metrics_after", {}),
        )
        return {"hint": hint}
    except Exception as e:
        logger.error(f"Copilot hint endpoint failed: {e}")
        return {"hint": ""}

@app.post("/explain", tags=["ai"])
async def explain(request: dict):
    try:
        explanation = await explain_health_change(
            diff=request.get("diff", {}),
            strategy_type=request.get("strategy_type", "custom"),
            entry_state=request.get("entry_state", {}),
            current_state=request.get("current_state", {}),
        )
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"Explain endpoint failed: {e}")
        return {"explanation": ""}

# ─── ASYNC WEBSOCKET LOOP ────────────────────────────────────────────────────
@app.websocket("/ws/health/{strategy_id}")
async def health_monitor_ws(websocket: WebSocket, strategy_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected | strategy_id={strategy_id}")

    entry = await snapshot.get_entry_state(strategy_id)
    if not entry:
        await websocket.send_json({"error": "strategy_not_found"})
        await websocket.close()
        return

    try:
        while True:
            chain, _ = await get_option_chain(entry["symbol"])
            current_spot, current_iv, dte = chain.get("spot", 19000), chain.get("current_iv", 0.15), chain.get("days_to_expiry", 30)
            
            legs = entry["legs"]
            current_delta = 0.0
            current_pnl = 0.0

            try:
                for leg in legs:
                    greeks = bs_compute(S=current_spot, K=leg["strike"], T_days=dte, r=0.065, sigma=current_iv, option_type=leg["option_type"])
                    qty, lot = leg.get("quantity", 1), leg.get("lot_size", 50)
                    multiplier = 1 if leg.get("side", "buy") == "buy" else -1
                    current_delta += greeks["delta"] * qty * lot * multiplier
                    entry_price = leg.get("entry_price", greeks["price"])
                    current_pnl += (greeks["price"] - entry_price) * qty * lot * multiplier
            except Exception as e:
                logger.error(f"WS Greek re-calc failed: {type(e).__name__} - {e}")
                current_delta = entry["entry_state"].get("portfolio_delta", 0.0)
                current_pnl = 0.0

            current_state = {"iv": current_iv, "spot": current_spot, "pnl": current_pnl, "portfolio_delta": current_delta, "days_to_expiry": dte}
            diff = health_monitor.compute_health_diff(entry["entry_state"], current_state)

            explanation = ""
            if diff.get("has_changes"):
                explanation = await explain_health_change(diff=diff, strategy_type=entry["strategy_type"], entry_state=entry["entry_state"], current_state=current_state)
                # Await the new async logging framework
                await snapshot.log_health_event(strategy_id, diff, explanation)

            payload = {"diff": diff, "explanation": explanation, "data_mode": "live", "checked_at": datetime.now(timezone.utc).isoformat()}
            await websocket.send_json(payload)
            await asyncio.sleep(settings.HEALTH_MONITOR_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected | strategy_id={strategy_id}")
    except Exception as e:
        logger.error(f"WebSocket error | strategy_id={strategy_id} | {type(e).__name__}: {e}")
        try:
            await websocket.send_json({"error": "monitor_error"})
            await websocket.close()
        except Exception:
            pass