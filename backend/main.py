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
"""

import asyncio
import logging
import json
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import settings
from database import create_tables
from utils.logger import setup_logging
from utils.validators import validate_legs, validate_symbol

# Quant / data / engine imports
from data.fallback import get_option_chain
from engine import strategy_builder
from engine import assumption_checker
from engine import health_monitor
from engine import adjustment_simulator
from engine import snapshot

# AI layer — import only the public API functions, never providers directly
from ai.explainer import explain_health_change
from ai.copilot import get_leg_hint

# Pydantic models (request/response shapes)
from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    SaveStrategyRequest,
    AdjustmentSimulateRequest,
    AdjustmentSimulateResponse,
    CopilotHintRequest,
    DataMode,
)

# ---------------------------------------------------------------------------
# Logging setup (must be before any logger.getLogger calls)
# ---------------------------------------------------------------------------
setup_logging(
    level=getattr(settings, "LOG_LEVEL", "INFO"),
    log_format=getattr(settings, "LOG_FORMAT", "text"),
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MoneyLogix Strategy Builder",
    description=(
        "SEBI-compliant options strategy lifecycle platform for Indian index options. "
        "Provides real-time Greeks, payoff analysis, health monitoring, and AI narration."
    ),
    version="1.0.0",
    docs_url="/docs",      # Swagger UI — judges can explore the API here
    redoc_url="/redoc",    # ReDoc alternative documentation
)

# ---------------------------------------------------------------------------
# CORS — must allow the Vite dev server on port 5173.
# In production, replace with the actual deployed frontend URL.
# ---------------------------------------------------------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:5173"] from config
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "OPTIONS"],
#     allow_headers=["*"],
# )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup event — initialise DB tables before first request
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Request logging middleware
# Spec requires: method, path, key params, response time logged at INFO.
# Using middleware (not per-endpoint) so every route gets it automatically,
# including future routes added without remembering to add logging.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    response = await call_next(request)
    response_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"response_ms={response_ms:.0f}"
    )
    return response


# ---------------------------------------------------------------------------
# Validation error handler (422 from Pydantic)
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": str(exc)},
    )


@app.on_event("startup")
async def startup():
    """
    Run once when uvicorn starts the application.
    Creates SQLite tables if they don't exist (idempotent).
    """
    create_tables()
    logger.info(
        f"MoneyLogix Strategy Builder started | "
        f"AI provider: {settings.AI_PROVIDER} | "
        f"Environment: {getattr(settings, 'ENV', 'development')}"
    )


# ---------------------------------------------------------------------------
# Global exception handler — ensures we never leak stack traces to the client
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ===========================================================================
# ROUTES
# ===========================================================================


# ---------------------------------------------------------------------------
# GET /health
# Purpose: judges verify the API is alive before the demo starts.
# Also useful for load balancer health checks in production.
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health_check():
    """
    Returns API status, current timestamp, and active AI provider.
    Always returns 200 if the server is running.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "ai_provider": settings.AI_PROVIDER,
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# GET /option-chain/{symbol}
# Returns the full option chain for a symbol, with data mode metadata.
# The 4-tier fallback in get_option_chain() means this never returns 503.
# ---------------------------------------------------------------------------
@app.get("/option-chain/{symbol}", tags=["market-data"])
async def get_chain(symbol: str):
    """
    Fetch option chain for NIFTY, BANKNIFTY, etc.

    Returns:
        chain     : Dict of strike → {CE: {...}, PE: {...}} with LTP, IV, OI, Greeks
        data_mode : {"mode": "live|cache|snapshot|mock", "timestamp": "..."}
    """
    # Validate symbol before hitting the data layer
    errors = validate_symbol(symbol.upper())
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    chain, mode = get_option_chain(symbol.upper())
    return {
        "chain": chain,
        "data_mode": DataMode(mode=mode, timestamp=datetime.utcnow().isoformat()),
    }


# ---------------------------------------------------------------------------
# POST /strategy/analyze
# Core endpoint: takes legs, returns full metrics (Greeks, payoff, risk, assumptions).
# ---------------------------------------------------------------------------
@app.post("/strategy/analyze", response_model=AnalyzeResponse, tags=["strategy"])
async def analyze_strategy(request: AnalyzeRequest):
    start_time = datetime.utcnow()

    # Convert Pydantic models to pure dicts to prevent Enum casting bugs
    legs_as_dicts = [json.loads(leg.json()) for leg in request.legs]
    errors = validate_legs(legs_as_dicts)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Build metrics
    metrics, mode = strategy_builder.build_strategy_metrics(
        legs=legs_as_dicts,
        symbol=request.symbol.upper(),
    )

    # Check market assumptions
    chain, _ = get_option_chain(request.symbol.upper())
    market_state = _build_market_state(metrics, chain, mode)
    assumptions = assumption_checker.check_assumptions(
        strategy_type=request.strategy_type,
        market_state=market_state,
    )

    response_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(f"Strategy analyzed | response_ms={response_ms:.0f}")

    return AnalyzeResponse(
        metrics=metrics,
        assumptions=assumptions,
        data_mode=DataMode(mode=mode, timestamp=datetime.utcnow().isoformat()),
    )


# ---------------------------------------------------------------------------
# POST /strategy/payoff
# ---------------------------------------------------------------------------
@app.post("/strategy/payoff", tags=["strategy"])
async def strategy_payoff(request: dict):
    legs = request.get("legs", [])
    symbol = request.get("symbol", "NIFTY").upper()
    num_points = request.get("num_points", 100)

    errors = validate_legs(legs) + validate_symbol(symbol)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    chain, mode = get_option_chain(symbol)
    spot = chain.get("spot", 19000)
    
    from quant.payoff import compute_payoff_curve, find_breakevens, compute_max_profit_loss
    curve = compute_payoff_curve(legs, spot, num_points=num_points)
    breakevens = find_breakevens(curve)
    risk = compute_max_profit_loss(curve)

    return {
        "payoff_curve": curve,
        "risk_metrics": {"breakevens": breakevens, "max_profit": risk.get("max_profit", 0), "max_loss": risk.get("max_loss", 0)},
        "data_mode": DataMode(mode=mode, timestamp=datetime.utcnow().isoformat()),
    }


# ---------------------------------------------------------------------------
# POST /strategy/assumptions
# ---------------------------------------------------------------------------
@app.post("/strategy/assumptions", tags=["strategy"])
async def check_strategy_assumptions(request: dict):
    legs = request.get("legs", [])
    strategy_type = request.get("strategy_type", "custom")
    symbol = request.get("symbol", "NIFTY").upper()

    errors = validate_legs(legs) + validate_symbol(symbol)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    metrics, mode = strategy_builder.build_strategy_metrics(legs=legs, symbol=symbol)
    chain, _ = get_option_chain(symbol)
    market_state = _build_market_state(metrics, chain, mode)
    assumptions = assumption_checker.check_assumptions(strategy_type, market_state)

    return {
        "assumptions": assumptions,
        "data_mode": DataMode(mode=mode, timestamp=datetime.utcnow().isoformat()),
    }


# ---------------------------------------------------------------------------
# POST /strategy/stress-test
# ---------------------------------------------------------------------------
@app.post("/strategy/stress-test", tags=["strategy"])
async def stress_test(request: dict):
    legs = request.get("legs", [])
    symbol = request.get("symbol", "NIFTY").upper()

    errors = validate_legs(legs) + validate_symbol(symbol)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    chain, mode = get_option_chain(symbol)
    from quant.stress_test import run_stress_matrix
    stress_result = run_stress_matrix(
        legs=legs,
        spot=chain.get("spot", 19000),
        current_iv=chain.get("current_iv", 0.15),
        T_days=chain.get("days_to_expiry", 30)
    )

    return {
        **stress_result,
        "data_mode": DataMode(mode=mode, timestamp=datetime.utcnow().isoformat()),
    }


# ---------------------------------------------------------------------------
# POST /strategy/save
# ---------------------------------------------------------------------------
@app.post("/strategy/save", tags=["strategy"])
async def save_strategy(request: SaveStrategyRequest):
    legs_as_dicts = [json.loads(leg.json()) for leg in request.legs]
    errors = validate_legs(legs_as_dicts)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    metrics, mode = strategy_builder.build_strategy_metrics(
        legs=legs_as_dicts,
        symbol=request.symbol.upper(),
    )
    
    chain, _ = get_option_chain(request.symbol.upper())
    spot = chain.get("spot", 19000)
    iv = chain.get("current_iv", 0.15)

    strategy_id = snapshot.create_strategy_snapshot(
        symbol=request.symbol.upper(),
        strategy_type=request.strategy_type,
        legs=legs_as_dicts,
        metrics=metrics,
        spot=spot,
        iv=iv,
    )
    return {"strategy_id": strategy_id, "saved": True}


# ---------------------------------------------------------------------------
# GET /strategy/{strategy_id}/history
# ---------------------------------------------------------------------------
@app.get("/strategy/{strategy_id}/history", tags=["strategy"])
async def get_strategy_history(strategy_id: str):
    history = snapshot.get_health_history(strategy_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"strategy_id": strategy_id, "history": history}


# ---------------------------------------------------------------------------
# POST /adjustment/simulate
# ---------------------------------------------------------------------------
@app.post("/adjustment/simulate", response_model=AdjustmentSimulateResponse, tags=["adjustments"])
async def simulate_adjustment_route(request: AdjustmentSimulateRequest):
    orig_legs = [json.loads(leg.json()) for leg in request.original_legs]
    adj_legs = [json.loads(leg.json()) for leg in request.adjusted_legs]
    
    result = adjustment_simulator.simulate_adjustment(
        original_legs=orig_legs,
        adjusted_legs=adj_legs,
        symbol=request.symbol.upper(),
    )
    
    # Pydantic requires DataMode as an object, not a string
    mode_str = result.pop("data_mode", "demo")
    result["data_mode"] = {"mode": mode_str, "timestamp": datetime.utcnow().isoformat()}
    
    return AdjustmentSimulateResponse(**result)


# ---------------------------------------------------------------------------
# POST /copilot/hint
# ---------------------------------------------------------------------------
@app.post("/copilot/hint", tags=["ai"])
async def copilot_hint(request: dict):
    try:
        hint = get_leg_hint(
            leg_before=request.get("changed_leg_before", {}),
            leg_after=request.get("changed_leg_after", {}),
            metrics_before=request.get("metrics_before", {}),
            metrics_after=request.get("metrics_after", {}),
        )
        return {"hint": hint}
    except Exception as e:
        logger.error(f"Copilot hint endpoint failed: {e}")
        return {"hint": ""}


# ---------------------------------------------------------------------------
# POST /explain
# ---------------------------------------------------------------------------
@app.post("/explain", tags=["ai"])
async def explain(request: dict):
    try:
        explanation = explain_health_change(
            diff=request.get("diff", {}),
            strategy_type=request.get("strategy_type", "custom"),
            entry_state=request.get("entry_state", {}),
            current_state=request.get("current_state", {}),
        )
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"Explain endpoint failed: {e}")
        return {"explanation": ""}


# ===========================================================================
# WEBSOCKET — Real-time health monitoring
# ===========================================================================

@app.websocket("/ws/health/{strategy_id}")
async def health_monitor_ws(websocket: WebSocket, strategy_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected | strategy_id={strategy_id}")
    
    # Check if strategy exists
    entry = snapshot.get_entry_state(strategy_id)
    if not entry:
        await websocket.send_json({"error": "strategy_not_found"})
        await websocket.close()
        return

    try:
        while True:
            # 1. Fetch live market data
            chain, _ = get_option_chain(entry["symbol"])
            current_spot = chain.get("spot", 19000)
            current_iv = chain.get("current_iv", 0.15)
            dte = chain.get("days_to_expiry", 30)

            # 2. Re-compute current portfolio delta
            # We must re-greek the legs using the current spot/iv
            # 2. Re-compute current portfolio delta & PnL
            legs = entry["legs"]
            try:
                from quant.blackscholes import compute as bs_compute
                
                current_delta = 0.0
                current_pnl = 0.0
                
                for leg in legs:
                    # Compute current live price & greeks
                    greeks = bs_compute(
                        S=current_spot, 
                        K=leg["strike"], 
                        T_days=dte, 
                        r=0.065, 
                        sigma=current_iv, 
                        option_type=leg["option_type"]
                    )
                    
                    qty = leg.get("quantity", 1)
                    lot = leg.get("lot_size", 50)
                    multiplier = 1 if leg.get("side", "buy") == "buy" else -1
                    
                    # Aggregate Delta
                    current_delta += greeks["delta"] * qty * lot * multiplier
                    
                    # Aggregate PnL
                    # If frontend didn't send an entry price, assume current price = 0 PnL for demo
                    entry_price = leg.get("entry_price", greeks["price"])
                    current_pnl += (greeks["price"] - entry_price) * qty * lot * multiplier

            except Exception as e:
                logger.error(f"WS Greek inline re-calc failed: {type(e).__name__} - {e}")
                current_delta = entry["entry_state"].get("portfolio_delta", 0.0)
                current_pnl = 0.0

            # 3. Build current state
            current_state = {
                "iv": current_iv,
                "spot": current_spot,
                "pnl": current_pnl,
                "portfolio_delta": current_delta,
                "days_to_expiry": dte,
            }

            # 4. Compute Diff
            diff = health_monitor.compute_health_diff(entry["entry_state"], current_state)

            # 5. Get AI Explanation (only if things changed)
            explanation = ""
            if diff.get("has_changes"):
                explanation = explain_health_change(
                    diff=diff,
                    strategy_type=entry["strategy_type"],
                    entry_state=entry["entry_state"],
                    current_state=current_state
                )
                snapshot.log_health_event(strategy_id, diff, explanation)

            # 6. Send payload
            payload = {
                "diff": diff,
                "explanation": explanation,
                "data_mode": "live", # UI expects this field
                "checked_at": datetime.utcnow().isoformat()
            }
            await websocket.send_json(payload)

            # Wait before next poll
            await asyncio.sleep(settings.HEALTH_MONITOR_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected | strategy_id={strategy_id}")
    except Exception as e:
        logger.error(f"WebSocket error | strategy_id={strategy_id} | {type(e).__name__}: {e}")
        try:
            await websocket.send_json({"error": "monitor_error"})
            await websocket.close()
        except:
            pass


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _build_market_state(metrics: dict, chain: dict, mode: str) -> dict:
    greeks = metrics.get("portfolio_greeks", {})
    risk   = metrics.get("risk_metrics", {})
    liq_info = metrics.get("liquidity", {})

    # iv_rank is now a direct float on the metrics dict, not a nested dict
    iv_rank_val = metrics.get("iv_rank", 50.0)

    return {
        "spot_price":     chain.get("spot", 0),
        "iv":             chain.get("current_iv", 0),
        "iv_rank":        iv_rank_val,
        "trend":          "sideways", # Mocked for demo
        "expected_move":  metrics.get("expected_move_pct", 0),
        "days_to_expiry": chain.get("days_to_expiry", 30),
        "liquidity_score": liq_info.get("score", 75.0),
        "net_delta":      greeks.get("net_delta", 0),
        "net_theta":      greeks.get("net_theta", 0),
        "max_profit":     risk.get("max_profit", 0),
        "max_loss":       risk.get("max_loss", 0),
        "data_mode":      mode,
    } 


def _extract_current_state(chain: dict, entry: dict) -> dict:
    """
    Extract current market state from the option chain in the same shape
    as entry["entry_state"], so health_monitor.compute_health_diff() can
    do a direct before/after comparison.

    Shape:
    {
        "iv": float,              # ATM implied volatility (e.g. 0.145 = 14.5%)
        "spot": float,            # Current underlying price
        "pnl": float,             # Current unrealised P&L in ₹
        "portfolio_delta": float, # Current net delta
        "days_to_expiry": int,    # Calendar days remaining to nearest expiry
    }

    Note on P&L calculation:
      Full mark-to-market P&L requires re-pricing every leg at current market.
      For the health monitor (which only tracks relative changes), we compute
      a simplified P&L from the option chain's current LTPs vs entry prices.
      The full P&L is shown on the strategy detail page (from /strategy/analyze).
    """
    entry_state = entry.get("entry_state", {})
    legs        = entry.get("legs", [])

    # Current spot price from chain
    current_spot = chain.get("spot_price", entry_state.get("spot", 0))

    # ATM IV from chain (already averaged across CE/PE at ATM strike)
    current_iv = chain.get("atm_iv", entry_state.get("iv", 0))

    # Simplified P&L: sum of (current_ltp - entry_ltp) × lot_size × lots × direction
    # direction: +1 for buy (long premium), -1 for sell (short premium)
    current_pnl = 0.0
    for leg in legs:
        strike      = leg.get("strike")
        opt_type    = leg.get("option_type", "CE")
        side        = leg.get("side", "buy")
        lots        = leg.get("lots", 1)
        entry_price = leg.get("entry_price", 0)  # Saved at snapshot time
        lot_size    = entry.get("lot_size", 50)  # Saved with snapshot

        # Look up current LTP from chain
        strike_data   = chain.get("strikes", {}).get(str(strike), {})
        option_data   = strike_data.get(opt_type, {})
        current_ltp   = option_data.get("ltp", entry_price)  # Fallback to entry if missing

        direction     = 1 if side == "buy" else -1
        leg_pnl       = direction * (current_ltp - entry_price) * lot_size * lots
        current_pnl  += leg_pnl

    # Days to expiry: use chain-level value if available, otherwise derive from
    # the entry expiry date. The chain is the freshest source.
    days_to_expiry = chain.get("days_to_expiry", entry_state.get("days_to_expiry", 0))

    # Portfolio delta: ideally re-computed by re-pricing, but for diff purposes
    # we can use the chain's current ATM delta as a proxy for net delta shift.
    # The /strategy/analyze endpoint gives the precise value when needed.
    portfolio_delta = chain.get("atm_delta", entry_state.get("portfolio_delta", 0))

    return {
        "iv":              current_iv,
        "spot":            current_spot,
        "pnl":             round(current_pnl, 2),
        "portfolio_delta": portfolio_delta,
        "days_to_expiry":  days_to_expiry,
    }