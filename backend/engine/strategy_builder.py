"""strategy_builder.py — Main orchestrator for strategy analysis."""
from typing import Any
import logging
from quant import (
    blackscholes,
    portfolio_greeks,
    payoff,
    probability,
    margin,
    liquidity,
    expected_move,
)
from quant.iv_rank import compute_iv_rank
from data.fallback import get_option_chain
from data.mock_data import asset_config

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.065

_GAMMA_REF_PER_UNIT = 0.003
_VEGA_REF_PCT_OF_NOTIONAL = 0.02
_CAPITAL_AT_RISK_REF_PCT = 0.15
_RISK_WEIGHTS = {
    "delta": 0.20,
    "gamma": 0.15,
    "vega": 0.20,
    "margin": 0.15,
    "max_loss": 0.30,
}
_UNLIMITED_LOSS_SENTINEL = -999999999
_UNLIMITED_LOSS_FLOOR = 70

def _safe_default_metrics() -> dict[str, Any]:
    return {
        "legs": [],
        "greeks_per_leg": [],
        "portfolio_greeks": {
            "net_delta": 0.0, "net_gamma": 0.0, "net_theta": 0.0, "net_vega": 0.0, "leg_contributions": [],
        },
        "risk_metrics": {
            "max_profit": 0.0, "max_loss": 0.0, "breakevens": [], "probability_of_profit": 0.0, "margin_required": 0.0,
        },
        "liquidity": {"score": 0.0, "label": "unknown", "spread_pct": 0.0},
        "payoff_curve": [],
        "iv_rank": 0.0,
        "expected_move_pct": 0.0,
    }

def _enrich_leg_with_iv(leg: dict, chain: dict) -> dict:
    enriched = dict(leg)
    try:
        strike = leg["strike"]
        option_type = leg["option_type"]
        matched_iv = None
        for cs in chain.get("strikes", []):
            if cs.get("strike") == strike:
                opt = cs.get(option_type, {})
                matched_iv = opt.get("iv")
                break
        if matched_iv is None:
            matched_iv = chain.get("current_iv")
        enriched["iv"] = matched_iv
    except Exception:
        enriched["iv"] = chain.get("current_iv")
    return enriched

def _compute_leg_greeks(spot: float, dte: int, enriched_legs: list[dict]) -> list[dict]:
    legs_with_greeks = []
    for leg in enriched_legs:
        leg_copy = dict(leg)
        try:
            greeks = blackscholes.compute(spot, leg["strike"], dte, RISK_FREE_RATE, leg["iv"], leg["option_type"])
            leg_copy["greeks"] = greeks
            if leg_copy.get("entry_price") is None:
                leg_copy["entry_price"] = greeks["price"]
        except Exception as e:
            logger.exception(f"Greeks failed for leg {leg.get('id')}: {e}")
            leg_copy["greeks"] = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "price": 0.0, "pop": 0.0}
            if leg_copy.get("entry_price") is None:
                leg_copy["entry_price"] = 0.0
        legs_with_greeks.append(leg_copy)
    return legs_with_greeks

def _find_atm_strike_prices(chain: dict, spot: float):
    strikes = chain.get("strikes", [])
    if not strikes:
        return None, None
    atm = min(strikes, key=lambda s: abs(s.get("strike", float("inf")) - spot))
    return atm.get("call", {}).get("ltp"), atm.get("put", {}).get("ltp")

# FIX: Added 'async' here and 'await' below
async def build_strategy_metrics(legs: list[dict], symbol: str = "NIFTY") -> tuple[dict, str]:
    metrics = _safe_default_metrics()
    mode = "unknown"
    try:
        # FIX: Await the async chain fetcher
        chain, mode = await get_option_chain(symbol)
        spot = chain["spot"]
        dte = chain["days_to_expiry"]
    except Exception as e:
        logger.exception(f"Chain fetch failed for {symbol}: {e}")
        return metrics, "unavailable"

    try:
        enriched = [_enrich_leg_with_iv(leg, chain) for leg in legs]
    except Exception as e:
        logger.exception("IV enrichment failed: %s", e)
        enriched = legs

    try:
        with_greeks = _compute_leg_greeks(spot, dte, enriched)
        metrics["legs"] = with_greeks
        metrics["greeks_per_leg"] = [leg.get("greeks") for leg in with_greeks]
    except Exception as e:
        logger.exception("Greeks computation failed: %s", e)
        with_greeks = enriched

    try:
        metrics["portfolio_greeks"] = portfolio_greeks.aggregate(with_greeks)
    except Exception as e:
        logger.exception("Portfolio aggregation failed: %s", e)

    curve = []
    try:
        curve = payoff.compute_payoff_curve(with_greeks, spot)
        metrics["payoff_curve"] = curve
    except Exception as e:
        logger.exception("Payoff curve failed: %s", e)

    try:
        metrics["risk_metrics"]["breakevens"] = payoff.find_breakevens(curve)
    except Exception as e:
        logger.exception("Breakeven failed: %s", e)

    try:
        pl = payoff.compute_max_profit_loss(curve, legs=with_greeks)
        metrics["risk_metrics"]["max_profit"] = pl.get("max_profit", 0.0)
        metrics["risk_metrics"]["max_loss"] = pl.get("max_loss", 0.0)
    except Exception as e:
        logger.exception("Max P/L failed: %s", e)

    try:
        pop = probability.get_strategy_pop(with_greeks)
        metrics["risk_metrics"]["probability_of_profit"] = float(pop.get("strategy_pop", 0.0))
    except Exception as e:
        logger.exception("PoP failed: %s", e)

    try:
        margin_info = margin.estimate_margin(with_greeks, spot)
        metrics["risk_metrics"]["margin_required"] = margin_info.get("estimated_margin", 0.0)
    except Exception as e:
        logger.exception("Margin failed: %s", e)

    try:
        scores = []
        for leg in with_greeks:
            try:
                strike = leg["strike"]
                opt = leg["option_type"]
                row = next((s for s in chain.get("strikes", []) if s.get("strike") == strike), None)
                if row is None: continue
                od = row.get(opt, {})
                scores.append(liquidity.compute_liquidity_score(
                    od.get("oi", 0), od.get("bid", 0.0), od.get("ask", 0.0), od.get("volume", 0)
                ))
            except Exception:
                continue
        valid = [s for s in scores if s is not None]
        if valid: metrics["liquidity"] = liquidity.strategy_liquidity(valid)
    except Exception as e:
        logger.exception("Liquidity failed: %s", e)

    try:
        cp, pp = _find_atm_strike_prices(chain, spot)
        if cp is not None and pp is not None:
            em = expected_move.from_straddle(cp, pp, spot)
            metrics["expected_move_pct"] = em.get("expected_move_pct", 0.0)
    except Exception as e:
        logger.exception("Expected move failed: %s", e)

    try:
        metrics["iv_rank"] = float(compute_iv_rank(chain["current_iv"], chain.get("iv_52w_high", 0.3), chain.get("iv_52w_low", 0.08)))
    except Exception as e:
        logger.exception("IV rank failed: %s", e)

    try:
        metrics["risk_score"] = _compute_risk_score(
            legs=with_greeks, portfolio_greeks=metrics["portfolio_greeks"], risk_metrics=metrics["risk_metrics"], liquidity=metrics["liquidity"],
        )
    except Exception as e:
        logger.exception("Risk score failed: %s", e)
        metrics["risk_score"] = {"score": 50, "tier": "Moderate", "color": "amber", "breakdown": {}, "interpretation": "Unavailable."}

    return metrics, mode

def _compute_risk_score(legs, portfolio_greeks, risk_metrics, liquidity):
    total_units = 0
    total_notional = 0
    for leg in legs:
        symbol = leg.get("symbol", "NIFTY").upper()
        fallback_lot = asset_config.get(symbol, {}).get("lot", 50)
        lot_size = leg.get("lot_size", fallback_lot)
        qty = leg.get("quantity", 1)
        total_units += qty * lot_size
        total_notional += leg.get("strike", 0) * qty * lot_size
        
    total_units = total_units or 1
    total_notional = total_notional or 1

    nd, ng, nv = portfolio_greeks.get("net_delta", 0.0), portfolio_greeks.get("net_gamma", 0.0), portfolio_greeks.get("net_vega", 0.0)
    max_loss, margin_req = risk_metrics.get("max_loss", 0), risk_metrics.get("margin_required", 0)

    delta_score = min(100.0, (abs(nd) / total_units) * 100)
    gamma_score = min(100.0, (abs(ng) / (total_units * _GAMMA_REF_PER_UNIT)) * 100)
    vega_score = min(100.0, (abs(nv) / (total_notional * _VEGA_REF_PCT_OF_NOTIONAL)) * 100)
    margin_score = min(100.0, (margin_req / (total_notional * _CAPITAL_AT_RISK_REF_PCT)) * 100)

    unlimited = max_loss <= _UNLIMITED_LOSS_SENTINEL
    max_loss_score = 100.0 if unlimited else min(100.0, (abs(max_loss) / (total_notional * _CAPITAL_AT_RISK_REF_PCT)) * 100)
    liq_score = 100.0 - liquidity.get("score", 75.0)

    weighted = (delta_score * 0.20 + gamma_score * 0.15 + vega_score * 0.20 + margin_score * 0.15 + max_loss_score * 0.30)
    raw = max(weighted, _UNLIMITED_LOSS_FLOOR) if unlimited else weighted
    score = int(min(100, max(0, round(raw))))

    if score <= 33: tier, color = "Conservative", "green"
    elif score <= 66: tier, color = "Moderate", "amber"
    else: tier, color = "Aggressive", "red"

    desc = "minimal" if abs(nd) < total_units * 0.1 else "low" if abs(nd) < total_units * 0.3 else "moderate" if abs(nd) < total_units * 0.5 else "high"
    loss_text = "unlimited" if unlimited else f"₹{abs(max_loss):,.0f}"
    
    return {
        "score": score, "tier": tier, "color": color,
        "breakdown": {"delta": round(delta_score), "gamma": round(gamma_score), "vega": round(vega_score), "margin": round(margin_score), "maxLoss": round(max_loss_score), "liquidity": round(liq_score)},
        "interpretation": f"Risks {loss_text} with {desc} directional exposure across {total_units} units."
    }

def compute_time_decay_series(legs, spot, current_iv, total_dte, r=0.065):
    try:
        days_offsets = [0, 1, 3, 7]
        label_map = {0: "Today", 1: "+1 day", 3: "+3 days", 7: "+7 days", 15: "+15 days", total_dte: "At Expiry"}
        if total_dte > 20: days_offsets.append(15)
        days_offsets.append(total_dte)
        days_offsets = sorted(set(d for d in days_offsets if d <= total_dte))

        entry_prices = []
        for leg in legs:
            leg_iv = leg.get("iv") or current_iv
            eg = blackscholes.compute(spot, leg["strike"], total_dte, r, leg_iv, leg["option_type"])
            entry_prices.append(eg.get("price", 0))

        lower, upper = spot * 0.88, spot * 1.12
        x_pts = [lower + i * ((upper - lower) / 60) for i in range(61)]

        snapshots = []
        for offset in days_offsets:
            remaining = max(total_dte - offset, 0)
            bs_dte = max(remaining, 0.001)
            theta_eroded = 0.0
            repriced = []
            for i, leg in enumerate(legs):
                ng = blackscholes.compute(spot, leg["strike"], bs_dte, r, current_iv, leg["option_type"])
                entry = leg.get("entry_price", entry_prices[i])
                theta_eroded += (ng.get("price", 0) - entry) * (1 if leg["side"] == "buy" else -1) * (leg["quantity"] * leg["lot_size"])
                repriced.append({**leg, "entry_price": entry, "greeks": ng})

            port = portfolio_greeks.aggregate(repriced)
            custom_curve = []
            for x in x_pts:
                pnl = 0.0
                for i, leg in enumerate(legs):
                    size = leg["quantity"] * leg["lot_size"]
                    dir = 1 if leg["side"] == "buy" else -1
                    if remaining <= 0:
                        sim = max(0, x - leg["strike"]) if leg["option_type"] == "call" else max(0, leg["strike"] - x)
                    else:
                        sim = blackscholes.compute(x, leg["strike"], bs_dte, r, current_iv, leg["option_type"]).get("price", 0)
                    entry = leg.get("entry_price", entry_prices[i])
                    pnl += (sim - entry) * dir * size
                custom_curve.append({"price": round(x, 2), "pnl": round(pnl, 2)})

            expiry_curve = payoff.compute_payoff_curve(repriced, spot)
            pl = payoff.compute_max_profit_loss(expiry_curve, legs=repriced)

            snapshots.append({
                "label": label_map.get(offset, f"+{offset}d"), "days_remaining": remaining, "payoff_curve": custom_curve,
                "net_theta_per_day": round(port.get("net_theta", 0), 2), "theta_eroded_since_entry": round(theta_eroded, 0),
                "max_profit": pl.get("max_profit", 0), "max_loss": pl.get("max_loss", 0),
                "portfolio_delta": round(port.get("net_delta", 0), 4), "portfolio_vega": round(port.get("net_vega", 0), 2)
            })

        entry_pl = payoff.compute_max_profit_loss(
            payoff.compute_payoff_curve([{**l, "entry_price": entry_prices[i]} for i, l in enumerate(legs)], spot), legs=legs
        )
        return {"snapshots": snapshots, "entry_max_profit": entry_pl.get("max_profit", 0), "entry_max_loss": entry_pl.get("max_loss", 0)}
    except Exception as e:
        logger.exception("Time decay failed: %s", e)
        return {"snapshots": [], "entry_max_profit": 0, "entry_max_loss": 0}