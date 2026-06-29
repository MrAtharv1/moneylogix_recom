"""
adjustment_simulator.py — Compare original strategy to a proposed adjustment.

When a trader considers changing their position (shifting a strike,
adding a hedge leg, closing one leg), this shows the before/after impact
on all key metrics simultaneously.

CRITICAL: Use the SAME market data snapshot for both computations.
If you fetch the option chain twice, you might get different prices and
the comparison becomes meaningless. Fetch once, use twice.

WHY THIS MATTERS SO MUCH HERE SPECIFICALLY:
Every other module in this engine fetches the chain once per call because
that's just normal efficient design. Here it's not just efficiency — it's
CORRECTNESS. If even a few seconds pass between two chain fetches, the
spot price ticks, IV shifts a hair, and the "before" and "after" metrics
are now computed against two different markets. The resulting delta
("adjusted reduces max loss by ₹800") would then be partly an artifact of
market movement, not the adjustment itself — actively misleading a trader
deciding whether to make a real change to their position. So this module
fetches the chain exactly once and feeds the identical chain object into
both the original and adjusted computations, holding the market constant
the way a controlled experiment holds everything but the one variable
you're testing.
"""

import logging

from engine.strategy_builder import (
    _enrich_leg_with_iv,
    _compute_leg_greeks,
    _find_atm_strike_prices,
    RISK_FREE_RATE,
)
from quant import portfolio_greeks, payoff, probability, margin, liquidity, expected_move
from quant.iv_rank import compute_iv_rank, classify_iv_regime
from data.fallback import get_option_chain

logger = logging.getLogger(__name__)


def _compute_with_chain(legs: list[dict], chain: dict) -> dict:
    # 1. Use safe 0.0 defaults instead of None to satisfy Pydantic
    metrics = {
        "legs": [],
        "greeks_per_leg": [],
        "portfolio_greeks": {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0},
        "risk_metrics": {
            "max_profit": 0.0, "max_loss": 0.0, "breakevens": [],
            "probability_of_profit": 0.0, "margin_required": 0.0,
        },
        "liquidity": {"score": 0.0, "label": "unknown", "spread_pct": 0.0},
        "payoff_curve": [],
        "iv_rank": 0.0,
        "expected_move_pct": 0.0,
    }

    spot = chain.get("spot", 19000)
    dte = chain.get("days_to_expiry", 30)

    try:
        enriched_legs = [_enrich_leg_with_iv(leg, chain) for leg in legs]
    except Exception:
        logger.exception("Leg IV enrichment failed in adjustment comparison")
        enriched_legs = legs

    try:
        legs_with_greeks = _compute_leg_greeks(spot, dte, enriched_legs)
        metrics["legs"] = legs_with_greeks
        metrics["greeks_per_leg"] = [leg.get("greeks") for leg in legs_with_greeks]
    except Exception:
        logger.exception("Greeks computation failed in adjustment comparison")
        legs_with_greeks = enriched_legs

    try:
        metrics["portfolio_greeks"] = portfolio_greeks.aggregate(legs_with_greeks)
    except Exception:
        logger.exception("Portfolio greeks aggregation failed in adjustment comparison")

    curve = []
    try:
        legs_with_entry_prices = []
        for leg in legs_with_greeks:
            leg_copy = dict(leg)
            greeks = leg.get("greeks") or {}
            leg_copy["entry_price"] = greeks.get("price", 0.0)
            legs_with_entry_prices.append(leg_copy)
        curve = payoff.compute_payoff_curve(legs_with_entry_prices, spot)
        metrics["payoff_curve"] = curve
    except Exception:
        logger.exception("Payoff curve computation failed in adjustment comparison")

    try:
        breakevens = payoff.find_breakevens(curve)
        metrics["risk_metrics"]["breakevens"] = breakevens
    except Exception:
        logger.exception("Breakeven detection failed in adjustment comparison")

    try:
        profit_loss = payoff.compute_max_profit_loss(curve)
        metrics["risk_metrics"]["max_profit"] = profit_loss.get("max_profit", 0.0)
        metrics["risk_metrics"]["max_loss"] = profit_loss.get("max_loss", 0.0)
    except Exception:
        logger.exception("Max profit/loss computation failed in adjustment comparison")

    try:
        if len(legs_with_greeks) <= 1:
            pop = probability.for_single_leg(
                spot, metrics["risk_metrics"]["breakevens"], dte, RISK_FREE_RATE,
                legs_with_greeks[0].get("iv", chain.get("current_iv", 0.15)) if legs_with_greeks else chain.get("current_iv", 0.15)
            )
        else:
            pop = probability.for_spread(spot, metrics["risk_metrics"]["breakevens"], dte, RISK_FREE_RATE, chain.get("current_iv", 0.15))
        metrics["risk_metrics"]["probability_of_profit"] = float(pop)
    except Exception:
        logger.exception("Probability of profit computation failed in adjustment comparison")

    try:
        margin_info = margin.estimate_margin(legs_with_greeks, spot)
        metrics["risk_metrics"]["margin_required"] = margin_info.get("estimated_margin", 0.0)
    except Exception:
        logger.exception("Margin estimation failed in adjustment comparison")

    try:
        leg_liquidity_scores = []
        for leg in legs_with_greeks:
            try:
                strike = leg["strike"]
                option_type = leg["option_type"]
                chain_row = next((s for s in chain.get("strikes", []) if s.get("strike") == strike), None)
                if chain_row is None:
                    continue
                opt_data = chain_row.get(option_type, {})
                leg_liquidity_scores.append(liquidity.compute_liquidity_score(
                    opt_data.get("oi"), opt_data.get("bid"), opt_data.get("ask"), opt_data.get("volume")
                ))
            except Exception:
                pass
        valid_scores = [s for s in leg_liquidity_scores if s is not None]
        if valid_scores:
            metrics["liquidity"] = liquidity.strategy_liquidity(valid_scores)
    except Exception:
        logger.exception("Liquidity computation failed entirely in adjustment comparison")

    try:
        atm_call_price, atm_put_price = _find_atm_strike_prices(chain, spot)
        if atm_call_price is not None and atm_put_price is not None:
            expected = expected_move.from_straddle(atm_call_price, atm_put_price, spot)
            metrics["expected_move_pct"] = expected.get("expected_move_pct", 0.0)
    except Exception:
        logger.exception("Expected move computation failed in adjustment comparison")

    try:
        rank = compute_iv_rank(chain.get("current_iv", 0.15), chain.get("iv_52w_high", 0.20), chain.get("iv_52w_low", 0.10))
        metrics["iv_rank"] = float(rank)
    except Exception:
        logger.exception("IV rank computation failed in adjustment comparison")

    return metrics


def _format_change(before: float, after: float, prefix: str = "₹") -> str:
    """
    Formats a before -> after change as a directional, human-readable
    string: "▲ ₹1,200 (+18%)" or "▼ ₹800 (-12%)".

    Handles unlimited values (999999999.0) gracefully:
    A strategy with theoretically unlimited max loss (e.g. a naked short
    call) is conventionally represented internally as a large sentinel
    number (999999999.0) rather than None/infinity, since None would
    break arithmetic and float('inf') breaks JSON serialization. But
    showing "▲ ₹999,999,999 (+5%)" to a trader would be nonsensical and
    alarming. So: if EITHER side of the comparison is at/above that
    sentinel, we report the change qualitatively ("Unlimited" risk
    profile unchanged, or now capped/uncapped) instead of doing fake
    arithmetic on a placeholder number.
    """
    UNLIMITED_SENTINEL = 999999999.0

    before_unlimited = before is not None and before >= UNLIMITED_SENTINEL
    after_unlimited = after is not None and after >= UNLIMITED_SENTINEL

    if before_unlimited and after_unlimited:
        return "Unlimited (unchanged)"
    if before_unlimited and not after_unlimited:
        return f"Now capped at {prefix}{after:,.0f} (was unlimited)"
    if after_unlimited and not before_unlimited:
        return f"Now unlimited (was {prefix}{before:,.0f})"

    if before is None or after is None:
        # One side genuinely couldn't be computed (a failed metric, not
        # an "unlimited" sentinel) — don't fabricate a percentage off a
        # missing number.
        return "N/A"

    change = after - before
    arrow = "▲" if change > 0 else ("▼" if change < 0 else "—")

    if before == 0:
        # Avoid division by zero for percentage; report absolute change
        # only when there's no baseline to compute a % off of.
        return f"{arrow} {prefix}{abs(change):,.0f}"

    pct = (change / abs(before)) * 100
    sign = "+" if pct >= 0 else "-"
    return f"{arrow} {prefix}{abs(change):,.0f} ({sign}{abs(pct):.0f}%)"


def _build_summary(comparison: dict) -> str:
    """
    Builds the factual, never-directive 1-sentence summary.

    HARD RULE: never use "should", "recommend", "consider", or any other
    advisory language — this product shows facts about what an adjustment
    DOES, and deliberately stays silent on what the trader OUGHT to do
    with that information. That's a real, intentional product/compliance
    boundary (a tool that tells retail traders what to do with their
    money edges toward investment advice, which carries a different
    regulatory weight than a tool that just shows them facts) — so the
    phrasing here is built from a fixed set of factual templates rather
    than free-form generation, to make that boundary impossible to
    accidentally cross.
    """
    delta_profit = comparison["delta_max_profit"]
    delta_loss = comparison["delta_max_loss"]
    delta_margin = comparison["delta_margin"]

    clauses = []

    if delta_profit is not None and abs(delta_profit) >= 1:
        verb = "increases" if delta_profit > 0 else "reduces"
        clauses.append(f"{verb} max profit by ₹{abs(delta_profit):,.0f}")

    if delta_loss is not None and abs(delta_loss) >= 1:
        # Note: max_loss is typically stored as a negative number
        # (loss = negative P&L). A delta_loss that is MORE negative means
        # loss got WORSE (bigger); less negative (closer to zero) means
        # loss improved (smaller). We phrase from the magnitude's
        # perspective so "reduces max loss" always means the genuinely
        # good outcome (smaller potential loss), regardless of the sign
        # convention under the hood.
        verb = "reduces" if delta_loss > 0 else "increases"
        clauses.append(f"{verb} max loss by ₹{abs(delta_loss):,.0f}")

    if delta_margin is not None and abs(delta_margin) >= 1:
        verb = "raises" if delta_margin > 0 else "lowers"
        clauses.append(f"{verb} margin by ₹{abs(delta_margin):,.0f}")

    if not clauses:
        return "This adjustment has no material impact on profit, loss, or margin."

    # Join clauses naturally: "X, but also Y and Z." pattern mirrors the
    # spec's own example phrasing style.
    if len(clauses) == 1:
        body = clauses[0]
    elif len(clauses) == 2:
        body = f"{clauses[0]} but also {clauses[1]}"
    else:
        body = f"{clauses[0]} but also {clauses[1]} and {clauses[2]}"

    return f"Adjusting the position {body}."


def simulate_adjustment(
    original_legs: list[dict],
    adjusted_legs: list[dict],
    symbol: str = "NIFTY",
) -> dict:
    """
    Returns comparison of original vs adjusted strategy metrics.

    Implementation:
    1. chain, mode = get_option_chain(symbol)  ← fetch ONCE
    2. orig_metrics = _compute_with_chain(original_legs, chain)
    3. adj_metrics = _compute_with_chain(adjusted_legs, chain)
    4. Build comparison dict

    Returns: {"original": orig_metrics, "adjusted": adj_metrics,
              "comparison": comparison, "data_mode": mode}
    """
    try:
        # ↓↓↓ THE ONE CHAIN FETCH FOR THIS ENTIRE CALL ↓↓↓
        # Both branches below MUST use this exact `chain` object — see
        # module docstring for why a second fetch would silently corrupt
        # the comparison.
        chain, mode = get_option_chain(symbol)
    except Exception:
        logger.exception("get_option_chain failed for symbol=%s in simulate_adjustment", symbol)
        empty_metrics = {
            "legs": [], "greeks_per_leg": [],
            "portfolio_greeks": {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0},
            "risk_metrics": {"max_profit": None, "max_loss": None, "breakevens": [],
                              "probability_of_profit": None, "margin_required": None},
            "liquidity": {"score": None, "rating": "unknown"},
            "payoff_curve": [], "iv_rank": {"iv_rank": None, "regime": "unknown"},
            "expected_move_pct": None,
        }
        return {
            "original": empty_metrics,
            "adjusted": empty_metrics,
            "comparison": {
                "delta_max_profit": None, "delta_max_loss": None, "delta_margin": None,
                "delta_net_theta": None,
                "max_profit_changed_by": "N/A", "max_loss_changed_by": "N/A",
                "margin_changed_by": "N/A",
                "summary": "Unable to compute adjustment comparison — market data unavailable.",
            },
            "data_mode": "unavailable",
        }

    orig_metrics = _compute_with_chain(original_legs, chain)
    adj_metrics = _compute_with_chain(adjusted_legs, chain)

    # --- Build the comparison dict ---
    # Each delta is computed defensively: if either side's underlying
    # metric is None (that one computation failed upstream), the delta
    # for it is also None rather than raising or silently treating None
    # as 0 (which would fabricate a fake delta on top of a missing
    # number — worse than just admitting we don't know).
    orig_risk = orig_metrics["risk_metrics"]
    adj_risk = adj_metrics["risk_metrics"]

    def _safe_delta(a, b):
        if a is None or b is None:
            return 0.0
        return b - a

    delta_max_profit = _safe_delta(orig_risk["max_profit"], adj_risk["max_profit"])
    delta_max_loss = _safe_delta(orig_risk["max_loss"], adj_risk["max_loss"])
    delta_margin = _safe_delta(orig_risk["margin_required"], adj_risk["margin_required"])

    orig_theta = orig_metrics["portfolio_greeks"].get("theta")
    adj_theta = adj_metrics["portfolio_greeks"].get("theta")
    delta_net_theta = _safe_delta(orig_theta, adj_theta)

    comparison = {
        "delta_max_profit": delta_max_profit,
        "delta_max_loss": delta_max_loss,
        "delta_margin": delta_margin,
        "delta_net_theta": delta_net_theta,
        "max_profit_changed_by": _format_change(orig_risk["max_profit"], adj_risk["max_profit"]),
        "max_loss_changed_by": _format_change(orig_risk["max_loss"], adj_risk["max_loss"]),
        "margin_changed_by": _format_change(orig_risk["margin_required"], adj_risk["margin_required"]),
    }
    comparison["summary"] = _build_summary(comparison)

    return {
        "original": orig_metrics,
        "adjusted": adj_metrics,
        "comparison": comparison,
        "data_mode": mode,
    }