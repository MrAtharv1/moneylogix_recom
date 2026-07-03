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
from quant.iv_rank import compute_iv_rank, classify_iv_regime
from data.fallback import get_option_chain

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.065

# ── Risk Score reference thresholds ───────────────────────────────────────
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
            "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0,
        },
        "risk_metrics": {
            "max_profit": 0.0, "max_loss": 0.0, "breakevens": [],
            "probability_of_profit": 0.0, "margin_required": 0.0,
        },
        "liquidity": {"score": 0.0, "label": "unknown", "spread_pct": 0.0},
        "payoff_curve": [], "iv_rank": 0.0, "expected_move_pct": 0.0,
    }

def _enrich_leg_with_iv(leg: dict, chain: dict) -> dict:
    enriched = dict(leg)
    try:
        strike = leg["strike"]
        option_type = leg["option_type"]
        matched_iv = None
        for chain_strike in chain.get("strikes", []):
            if chain_strike.get("strike") == strike:
                option_data = chain_strike.get(option_type, {})
                matched_iv = option_data.get("iv")
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
        except Exception:
            leg_copy["greeks"] = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0, "price": None}
        legs_with_greeks.append(leg_copy)
    return legs_with_greeks

def _find_atm_strike_prices(chain: dict, spot: float) -> tuple[float | None, float | None]:
    strikes = chain.get("strikes", [])
    if not strikes:
        return None, None
    atm = min(strikes, key=lambda s: abs(s.get("strike", float("inf")) - spot))
    return atm.get("call", {}).get("ltp"), atm.get("put", {}).get("ltp")

def build_strategy_metrics(legs: list[dict], symbol: str = "NIFTY") -> tuple[dict, str]:
    metrics = _safe_default_metrics()
    mode = "unknown"
    try:
        chain, mode = get_option_chain(symbol)
        spot = chain["spot"]
        dte = chain["days_to_expiry"]
    except Exception:
        return metrics, "unavailable"
    
    try:
        enriched_legs = [_enrich_leg_with_iv(leg, chain) for leg in legs]
    except Exception:
        enriched_legs = legs
        
    try:
        legs_with_greeks = _compute_leg_greeks(spot, dte, enriched_legs)
        metrics["legs"] = legs_with_greeks
        metrics["greeks_per_leg"] = [leg.get("greeks") for leg in legs_with_greeks]
    except Exception:
        legs_with_greeks = enriched_legs
        
    try:
        metrics["portfolio_greeks"] = portfolio_greeks.aggregate(legs_with_greeks)
    except Exception:
        pass

    curve = []
    try:
        legs_with_entry_prices = []
        for leg in legs_with_greeks:
            leg_copy = dict(leg)
            greeks = leg.get("greeks") or {}
            leg_copy["entry_price"] = greeks.get("price")
            legs_with_entry_prices.append(leg_copy)
        curve = payoff.compute_payoff_curve(legs_with_entry_prices, spot)
        metrics["payoff_curve"] = curve
        metrics["legs"] = legs_with_entry_prices
    except Exception:
        pass

    breakevens: list[float] = []
    try:
        breakevens = payoff.find_breakevens(curve)
        metrics["risk_metrics"]["breakevens"] = breakevens
    except Exception:
        pass

    try:
        profit_loss = payoff.compute_max_profit_loss(curve)
        metrics["risk_metrics"]["max_profit"] = profit_loss.get("max_profit")
        metrics["risk_metrics"]["max_loss"] = profit_loss.get("max_loss")
    except Exception:
        pass

    try:
        if len(legs_with_greeks) <= 1:
            pop = probability.for_single_leg(spot, breakevens, dte, RISK_FREE_RATE, legs_with_greeks[0].get("iv", chain.get("current_iv", 0.15)) if legs_with_greeks else chain.get("current_iv", 0.15))
        else:
            pop = probability.for_spread(spot, breakevens, dte, RISK_FREE_RATE, chain.get("current_iv", 0.15))
        metrics["risk_metrics"]["probability_of_profit"] = float(pop)
    except Exception:
        pass

    try:
        margin_info = margin.estimate_margin(legs_with_greeks, spot)
        metrics["risk_metrics"]["margin_required"] = margin_info.get("estimated_margin", 0.0)
    except Exception:
        pass

    try:
        leg_liquidity_scores = []
        for leg in legs_with_greeks:
            try:
                strike = leg["strike"]
                option_type = leg["option_type"]
                chain_row = next((s for s in chain.get("strikes", []) if s.get("strike") == strike), None)
                if chain_row is None:
                    leg_liquidity_scores.append(None)
                    continue
                opt_data = chain_row.get(option_type, {})
                leg_liq = liquidity.compute_liquidity_score(opt_data.get("oi"), opt_data.get("bid"), opt_data.get("ask"), opt_data.get("volume"))
                leg_liquidity_scores.append(leg_liq)
            except Exception:
                leg_liquidity_scores.append(None)
        valid_scores = [s for s in leg_liquidity_scores if s is not None]
        if valid_scores:
            metrics["liquidity"] = liquidity.strategy_liquidity(valid_scores)
    except Exception:
        pass

    try:
        atm_call_price, atm_put_price = _find_atm_strike_prices(chain, spot)
        if atm_call_price is not None and atm_put_price is not None:
            expected = expected_move.from_straddle(atm_call_price, atm_put_price, spot)
            metrics["expected_move_pct"] = expected.get("expected_move_pct")
    except Exception:
        pass

    try:
        metrics["iv_rank"] = float(compute_iv_rank(chain["current_iv"], chain["iv_52w_high"], chain["iv_52w_low"]))
    except Exception:
        pass

    # Hybrid Risk Score
    try:
        metrics["risk_score"] = _compute_risk_score(
            legs=legs_with_greeks,
            portfolio_greeks=metrics.get("portfolio_greeks", {}),
            risk_metrics=metrics.get("risk_metrics", {}),
            liquidity=metrics.get("liquidity", {}),
        )
    except Exception:
        metrics["risk_score"] = {"score": 50, "tier": "Moderate", "color": "amber", "breakdown": {}, "interpretation": ""}

    return metrics, mode


def _compute_risk_score(legs: list[dict], portfolio_greeks: dict, risk_metrics: dict, liquidity: dict) -> dict:
    total_units = sum(leg.get("quantity", 1) * leg.get("lot_size", 50) for leg in legs) or 1
    total_notional = sum(leg.get("strike", 0) * leg.get("quantity", 1) * leg.get("lot_size", 50) for leg in legs) or 1
    
    net_delta = portfolio_greeks.get("net_delta", 0.0)
    net_gamma = portfolio_greeks.get("net_gamma", 0.0)
    net_vega = portfolio_greeks.get("net_vega", 0.0)
    max_loss = risk_metrics.get("max_loss", 0)
    margin_required = risk_metrics.get("margin_required", 0)

    delta_score = min(100.0, (abs(net_delta) / total_units) * 100)
    gamma_score = min(100.0, (abs(net_gamma) / (total_units * _GAMMA_REF_PER_UNIT)) * 100)
    vega_score = min(100.0, (abs(net_vega) / (total_notional * _VEGA_REF_PCT_OF_NOTIONAL)) * 100)
    margin_score = min(100.0, (margin_required / (total_notional * _CAPITAL_AT_RISK_REF_PCT)) * 100)
    
    max_loss_unlimited = max_loss <= _UNLIMITED_LOSS_SENTINEL
    max_loss_score = 100.0 if max_loss_unlimited else min(100.0, (abs(max_loss) / (total_notional * _CAPITAL_AT_RISK_REF_PCT)) * 100)
    liquidity_score = 100.0 - liquidity.get("score", 75.0)

    weighted = (
        delta_score * _RISK_WEIGHTS["delta"]
        + gamma_score * _RISK_WEIGHTS["gamma"]
        + vega_score * _RISK_WEIGHTS["vega"]
        + margin_score * _RISK_WEIGHTS["margin"]
        + max_loss_score * _RISK_WEIGHTS["max_loss"]
    )
    
    raw = max(weighted, _UNLIMITED_LOSS_FLOOR) if max_loss_unlimited else weighted
    score = int(min(100, max(0, round(raw))))
    
    if score <= 33: tier, color = "Conservative", "green"
    elif score <= 66: tier, color = "Moderate", "amber"
    else: tier, color = "Aggressive", "red"

    delta_desc = "minimal" if abs(net_delta) < total_units * 0.1 else "low" if abs(net_delta) < total_units * 0.3 else "moderate" if abs(net_delta) < total_units * 0.5 else "high"
    max_loss_text = "unlimited capital" if max_loss_unlimited else f"₹{abs(max_loss):,.0f}"
    
    return {
        "score": score, "tier": tier, "color": color,
        "breakdown": {
            "delta": round(delta_score), "gamma": round(gamma_score), "vega": round(vega_score),
            "margin": round(margin_score), "maxLoss": round(max_loss_score), "liquidity": round(liquidity_score),
        },
        "interpretation": f"This strategy risks {max_loss_text} with {delta_desc} directional exposure across {total_units} units."
    }


def compute_time_decay_series(legs: list[dict], spot: float, current_iv: float, total_dte: int, r: float = 0.065) -> dict:
    try:
        days_offsets = [0, 1, 3, 7]
        label_map = {0: "Today", 1: "+1 day", 3: "+3 days", 7: "+7 days", 15: "+15 days", total_dte: "At Expiry"}
        
        if total_dte > 20: days_offsets.append(15)
        days_offsets.append(total_dte)
        days_offsets = sorted(set(d for d in days_offsets if d <= total_dte))

        entry_prices = []
        for leg in legs:
            leg_iv = leg.get("iv") or current_iv
            entry_g = blackscholes.compute(spot, leg["strike"], total_dte, r, leg_iv, leg["option_type"])
            entry_prices.append(entry_g.get("price", 0))

        lower_bound, upper_bound = spot * 0.88, spot * 1.12
        x_points = [lower_bound + (i * ((upper_bound - lower_bound) / 60)) for i in range(61)]

        snapshots = []
        for offset in days_offsets:
            remaining_dte = max(total_dte - offset, 0)
            bs_dte = max(remaining_dte, 0.001)  
            
            theta_eroded = 0.0
            repriced_legs = []
            
            for i, leg in enumerate(legs):
                new_g = blackscholes.compute(spot, leg["strike"], bs_dte, r, current_iv, leg["option_type"])
                theta_eroded += (new_g.get("price", 0) - entry_prices[i]) * (1 if leg["side"] == "buy" else -1) * (leg["quantity"] * leg["lot_size"])
                repriced_legs.append({**leg, "entry_price": entry_prices[i], "greeks": new_g})

            portfolio = portfolio_greeks.aggregate(repriced_legs)

            custom_curve = []
            for x in x_points:
                point_pnl = 0.0
                for i, leg in enumerate(legs):
                    size = leg["quantity"] * leg["lot_size"]
                    direction = 1 if leg["side"] == "buy" else -1
                    if remaining_dte <= 0:
                        sim_price = max(0, x - leg["strike"]) if leg["option_type"] == "call" else max(0, leg["strike"] - x)
                    else:
                        sim_price = blackscholes.compute(x, leg["strike"], bs_dte, r, current_iv, leg["option_type"]).get("price", 0)
                    point_pnl += (sim_price - entry_prices[i]) * direction * size
                custom_curve.append({"price": round(x, 2), "pnl": round(point_pnl, 2)})

            expiry_curve = payoff.compute_payoff_curve(repriced_legs, spot)
            pl = payoff.compute_max_profit_loss(expiry_curve)

            snapshots.append({
                "label": label_map.get(offset, f"+{offset} days"),
                "days_remaining": remaining_dte,
                "payoff_curve": custom_curve,
                "net_theta_per_day": round(portfolio.get("net_theta", 0), 2),
                "theta_eroded_since_entry": round(theta_eroded, 0),
                "max_profit": pl.get("max_profit", 0),
                "max_loss": pl.get("max_loss", 0),
                "portfolio_delta": round(portfolio.get("net_delta", 0), 4),
                "portfolio_vega": round(portfolio.get("net_vega", 0), 2)
            })

        entry_pl = payoff.compute_max_profit_loss(payoff.compute_payoff_curve([{**l, "entry_price": entry_prices[i]} for i, l in enumerate(legs)], spot))
        return {"snapshots": snapshots, "entry_max_profit": entry_pl.get("max_profit", 0), "entry_max_loss": entry_pl.get("max_loss", 0)}
    except Exception:
        logger.exception("compute_time_decay_series failed")
        return {"snapshots": [], "entry_max_profit": 0, "entry_max_loss": 0}