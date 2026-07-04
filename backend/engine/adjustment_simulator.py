"""adjustment_simulator.py — Compare original strategy to a proposed adjustment."""
import logging
from engine.strategy_builder import (
    _enrich_leg_with_iv,
    _compute_leg_greeks,
    _find_atm_strike_prices,
    _compute_risk_score,
    RISK_FREE_RATE,
    _safe_default_metrics,
)
from quant import portfolio_greeks, payoff, probability, margin, liquidity, expected_move
from quant.iv_rank import compute_iv_rank
from data.fallback import get_option_chain

logger = logging.getLogger(__name__)

UNLIMITED_PROFIT = 999999999.0
UNLIMITED_LOSS = -999999999.0

def _compute_with_chain(legs: list[dict], chain: dict) -> dict:
    metrics = _safe_default_metrics()
    spot = chain.get("spot", 19000)
    dte = chain.get("days_to_expiry", 30)

    try:
        enriched = [_enrich_leg_with_iv(leg, chain) for leg in legs]
    except Exception:
        enriched = legs

    try:
        with_greeks = _compute_leg_greeks(spot, dte, enriched)
        metrics["legs"] = with_greeks
        metrics["greeks_per_leg"] = [leg.get("greeks") for leg in with_greeks]
    except Exception:
        with_greeks = enriched

    try:
        metrics["portfolio_greeks"] = portfolio_greeks.aggregate(with_greeks)
    except Exception:
        pass

    curve = []
    try:
        legs_with_entry = []
        for leg in with_greeks:
            lc = dict(leg)
            if lc.get("entry_price") is None:
                g = leg.get("greeks", {})
                lc["entry_price"] = g.get("price", 0.0)
            legs_with_entry.append(lc)
        curve = payoff.compute_payoff_curve(legs_with_entry, spot)
        metrics["payoff_curve"] = curve
    except Exception:
        pass

    try:
        metrics["risk_metrics"]["breakevens"] = payoff.find_breakevens(curve)
    except Exception:
        pass

    try:
        pl = payoff.compute_max_profit_loss(curve, legs=with_greeks)
        metrics["risk_metrics"]["max_profit"] = pl.get("max_profit", 0.0)
        metrics["risk_metrics"]["max_loss"] = pl.get("max_loss", 0.0)
    except Exception:
        pass

    try:
        pop = probability.get_strategy_pop(with_greeks)
        metrics["risk_metrics"]["probability_of_profit"] = float(pop.get("strategy_pop", 0.0))
    except Exception:
        pass

    try:
        margin_info = margin.estimate_margin(with_greeks, spot)
        metrics["risk_metrics"]["margin_required"] = margin_info.get("estimated_margin", 0.0)
    except Exception:
        pass

    try:
        scores = []
        for leg in with_greeks:
            try:
                strike = leg["strike"]
                opt = leg["option_type"]
                row = next((s for s in chain.get("strikes", []) if s.get("strike") == strike), None)
                if row is None: continue
                od = row.get(opt, {})
                scores.append(liquidity.compute_liquidity_score(od.get("oi", 0), od.get("bid", 0.0), od.get("ask", 0.0), od.get("volume", 0)))
            except Exception:
                continue
        valid = [s for s in scores if s is not None]
        if valid: metrics["liquidity"] = liquidity.strategy_liquidity(valid)
    except Exception:
        pass

    try:
        cp, pp = _find_atm_strike_prices(chain, spot)
        if cp is not None and pp is not None:
            em = expected_move.from_straddle(cp, pp, spot)
            metrics["expected_move_pct"] = em.get("expected_move_pct", 0.0)
    except Exception:
        pass

    try:
        rank = compute_iv_rank(chain.get("current_iv", 0.15), chain.get("iv_52w_high", 0.20), chain.get("iv_52w_low", 0.10))
        metrics["iv_rank"] = float(rank)
    except Exception:
        pass

    try:
        metrics["risk_score"] = _compute_risk_score(legs=with_greeks, portfolio_greeks=metrics["portfolio_greeks"], risk_metrics=metrics["risk_metrics"], liquidity=metrics["liquidity"])
    except Exception:
        metrics["risk_score"] = {"score": 50, "tier": "Moderate", "color": "amber", "breakdown": {}, "interpretation": ""}

    return metrics

def _format_change(before: float, after: float, prefix: str = "₹") -> str:
    before_up = before is not None and before >= UNLIMITED_PROFIT
    after_up = after is not None and after >= UNLIMITED_PROFIT
    before_down = before is not None and before <= UNLIMITED_LOSS
    after_down = after is not None and after <= UNLIMITED_LOSS

    if (before_up and after_up) or (before_down and after_down): return "Unlimited (unchanged)"
    if before_up and not after_up: return f"Now capped at {prefix}{after:,.0f} (was unlimited profit)"
    if after_up and not before_up: return f"Now unlimited profit (was {prefix}{before:,.0f})"
    if before_down and not after_down: return f"Now capped at {prefix}{abs(after):,.0f} (was unlimited loss)"
    if after_down and not before_down: return f"Now unlimited loss (was {prefix}{abs(before):,.0f})"

    if before is None or after is None: return "N/A"
    change = after - before
    arrow = "▲" if change > 0 else ("▼" if change < 0 else "—")
    if before == 0: return f"{arrow} {prefix}{abs(change):,.0f}"
    pct = (change / abs(before)) * 100
    sign = "+" if pct >= 0 else "-"
    return f"{arrow} {prefix}{abs(change):,.0f} ({sign}{abs(pct):.0f}%)"

def _build_summary(comp: dict) -> str:
    clauses = []
    dp = comp.get("delta_max_profit")
    if dp is not None and abs(dp) >= 1: clauses.append(f"{'increases' if dp > 0 else 'reduces'} max profit by ₹{abs(dp):,.0f}")
    dl = comp.get("delta_max_loss")
    if dl is not None and abs(dl) >= 1: clauses.append(f"{'reduces' if dl > 0 else 'increases'} max loss by ₹{abs(dl):,.0f}")
    dm = comp.get("delta_margin")
    if dm is not None and abs(dm) >= 1: clauses.append(f"{'raises' if dm > 0 else 'lowers'} margin by ₹{abs(dm):,.0f}")

    if not clauses: return "This adjustment has no material impact."
    body = clauses[0] if len(clauses) == 1 else f"{clauses[0]} but also {clauses[1]}" if len(clauses) == 2 else f"{clauses[0]} but also {clauses[1]} and {clauses[2]}"
    return f"Adjusting the position {body}."

# FIX: Added async/await
async def simulate_adjustment(original_legs: list[dict], adjusted_legs: list[dict], symbol: str = "NIFTY") -> dict:
    try:
        chain, mode = await get_option_chain(symbol)
    except Exception as e:
        logger.exception("Chain fetch failed in simulate_adjustment: %s", symbol)
        empty = _safe_default_metrics()
        return {
            "original": empty, "adjusted": empty,
            "comparison": {"delta_max_profit": 0.0, "delta_max_loss": 0.0, "delta_margin": 0.0, "delta_net_theta": 0.0, "max_profit_changed_by": "N/A", "max_loss_changed_by": "N/A", "margin_changed_by": "N/A", "summary": "Market data unavailable."},
            "data_mode": "unavailable",
        }

    orig = _compute_with_chain(original_legs, chain)
    adj = _compute_with_chain(adjusted_legs, chain)

    def safe_delta(a, b): return 0.0 if a is None or b is None else b - a

    or_risk = orig["risk_metrics"]
    aj_risk = adj["risk_metrics"]

    comp = {
        "delta_max_profit": safe_delta(or_risk["max_profit"], aj_risk["max_profit"]),
        "delta_max_loss": safe_delta(or_risk["max_loss"], aj_risk["max_loss"]),
        "delta_margin": safe_delta(or_risk["margin_required"], aj_risk["margin_required"]),
        "delta_net_theta": safe_delta(orig["portfolio_greeks"].get("net_theta"), adj["portfolio_greeks"].get("net_theta")),
        "max_profit_changed_by": _format_change(or_risk["max_profit"], aj_risk["max_profit"]),
        "max_loss_changed_by": _format_change(or_risk["max_loss"], aj_risk["max_loss"]),
        "margin_changed_by": _format_change(or_risk["margin_required"], aj_risk["margin_required"]),
    }
    comp["summary"] = _build_summary(comp)

    return {"original": orig, "adjusted": adj, "comparison": comp, "data_mode": mode}