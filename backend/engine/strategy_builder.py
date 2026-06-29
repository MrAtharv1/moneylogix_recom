"""
strategy_builder.py — Main orchestrator for strategy analysis.

Given a list of option legs, computes all metrics by coordinating
the quant/* modules. This is what the FastAPI /strategy/analyze
endpoint calls. One function, everything computed.

DESIGN PHILOSOPHY — "degrade, don't die":
A strategy analysis touches ~10 independent calculations (Greeks, payoff,
probability, margin, liquidity, IV rank, expected move...). If we let any
single one raise an exception, the trader gets a 500 error and sees nothing
at all — even though 9 out of 10 numbers were perfectly fine to compute.

So every step here is isolated in its own try/except. A failure in, say,
IV-rank computation (maybe the 52-week high/low isn't cached yet) should
never take down the Greeks or the payoff curve. We log the failure and
substitute a safe, clearly-labeled default so the UI can show "N/A"
instead of crashing.
"""

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

# Risk-free rate used across all Black-Scholes calls in this module.
# 6.5% approximates the short-term Indian G-Sec / T-Bill yield, which is
# the standard proxy for "risk-free" when pricing NSE index options.
# Hardcoded (not fetched live) because it moves slowly and a live RBI
# rate feed would be a lot of plumbing for a number that barely matters —
# options pricing is far more sensitive to IV and time than to a 50bps
# wobble in the risk-free rate.
RISK_FREE_RATE = 0.065


def _safe_default_metrics() -> dict[str, Any]:
    """
    The full "everything failed" shape. Guarantees Pydantic model compliance.
    """
    return {
        "legs": [],
        "greeks_per_leg": [],
        "portfolio_greeks": {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
        },
        "risk_metrics": {
            "max_profit": 0.0,
            "max_loss": 0.0,
            "breakevens": [],
            "probability_of_profit": 0.0,
            "margin_required": 0.0,
        },
        "liquidity": {
            "score": 0.0,
            "label": "unknown",
            "spread_pct": 0.0
        },
        "payoff_curve": [],
        "iv_rank": 0.0,
        "expected_move_pct": 0.0,
    }

def _enrich_leg_with_iv(leg: dict, chain: dict) -> dict:
    """
    Step 4 — attach a live implied volatility to a leg.

    WHY THIS MATTERS: a leg's Greeks depend on the IV the market is
    currently pricing for *that specific strike and option type* — not
    some average IV for the underlying. Different strikes trade at
    different IVs (the "volatility skew/smile"). Pulling the strike-
    specific IV from the live chain, rather than reusing one IV for every
    leg, is what makes the Greeks reflect reality instead of a textbook
    approximation.

    Matching logic:
      1. Find the chain entry whose strike equals this leg's strike.
      2. From that entry, pull the IV for the matching option_type
         (a strike has separate call IV and put IV — they aren't equal
         when skew is present).
      3. If no exact strike match exists in the chain (e.g. an odd strike,
         or stale/partial chain data), fall back to the underlying's
         overall current_iv so the calculation can still proceed instead
         of blocking the whole leg.
    """
    enriched = dict(leg)  # never mutate the caller's leg dict
    try:
        strike = leg["strike"]
        option_type = leg["option_type"]  # "call" or "put"

        matched_iv = None
        for chain_strike in chain.get("strikes", []):
            if chain_strike.get("strike") == strike:
                # Each strike row carries iv per side, e.g. {"call_iv": .., "put_iv": ..}
                iv_key = f"{option_type}_iv"
                if iv_key in chain_strike:
                    matched_iv = chain_strike[iv_key]
                break

        if matched_iv is None:
            # No strike match (or missing IV field for that side) — fall
            # back to the underlying-level IV rather than failing the leg.
            matched_iv = chain.get("current_iv")
            logger.info(
                "No chain IV match for strike=%s type=%s; using chain current_iv=%s fallback",
                strike, option_type, matched_iv,
            )

        enriched["iv"] = matched_iv
    except Exception:
        logger.exception("Failed to enrich leg with IV; leg=%s", leg)
        enriched["iv"] = chain.get("current_iv")  # best-effort fallback
    return enriched


def _compute_leg_greeks(spot: float, dte: int, enriched_legs: list[dict]) -> list[dict]:
    """
    Step 5 — Black-Scholes Greeks for every leg, individually.

    We compute Greeks per-leg (not just at the portfolio level) because:
      - The UI shows a per-leg breakdown so traders see which leg is
        driving the position's risk.
      - Portfolio Greeks are just the (quantity-weighted, sign-adjusted)
        sum of leg Greeks — you need the leg-level numbers first to be
        able to sum them in portfolio_greeks.aggregate().

    blackscholes.compute() returns {delta, gamma, theta, vega, rho, price}
    for one option, using:
      S = spot price of the underlying
      K = leg["strike"]
      T = dte (time to expiry, in days — converted to years inside the
          quant module)
      r = RISK_FREE_RATE
      sigma = the leg's own IV (from step 4 — this is what makes each
          leg's Greeks reflect its own slice of the vol smile)
      option_type = call or put, since the payoff (and therefore every
          Greek) differs structurally between the two.
    """
    legs_with_greeks = []
    for leg in enriched_legs:
        leg_copy = dict(leg)
        try:
            greeks = blackscholes.compute(
                spot,
                leg["strike"],
                dte,
                RISK_FREE_RATE,
                leg["iv"],
                leg["option_type"],
            )
            leg_copy["greeks"] = greeks
        except Exception:
            logger.exception("Black-Scholes computation failed for leg=%s", leg)
            # Zeroed Greeks are a safe neutral default: they won't distort
            # the portfolio aggregation (adding zero changes nothing), and
            # the UI can detect price=None to show "Greeks unavailable"
            # for this specific leg without blanking the whole strategy.
            leg_copy["greeks"] = {
                "delta": 0.0, "gamma": 0.0, "theta": 0.0,
                "vega": 0.0, "rho": 0.0, "price": None,
            }
        legs_with_greeks.append(leg_copy)
    return legs_with_greeks


def _find_atm_strike_prices(chain: dict, spot: float) -> tuple[float | None, float | None]:
    """
    Helper for step 15 — locate the at-the-money (ATM) strike's call and
    put last-traded prices, needed for the straddle-implied expected move.

    ATM = the strike closest to the current spot price. We use the ATM
    straddle (long one call + one put at the same strike) because its
    combined premium is the market's own real-time estimate of how far
    the underlying is expected to move by expiry — no model required,
    just observed prices. This is more "honest" than a theoretical
    sigma*sqrt(T) estimate because it bakes in whatever the market
    currently thinks (including skew, event risk, etc.).
    """
    strikes = chain.get("strikes", [])
    if not strikes:
        return None, None

    # min() with a key= of "distance from spot" finds the closest strike —
    # this is the standard, simplest way to identify "the" ATM strike
    # without needing strikes to be sorted or evenly spaced.
    atm = min(strikes, key=lambda s: abs(s.get("strike", float("inf")) - spot))
    call_price = atm.get("call_ltp")
    put_price = atm.get("put_ltp")
    return call_price, put_price


def build_strategy_metrics(legs: list[dict], symbol: str = "NIFTY") -> tuple[dict, str]:
    """
    Main entry point. Returns (metrics_dict, data_mode_string).

    data_mode_string comes straight from get_option_chain() and tells the
    caller which tier of the 4-tier fallback served this data (live NSE,
    cache, snapshot, or mock) — important context for the UI to show a
    "data may be delayed" banner when we're not on live data.
    """
    metrics = _safe_default_metrics()
    mode = "unknown"

    # ---- Steps 1-3: fetch the option chain (this is foundational — if
    # this fails entirely there is genuinely nothing else we can compute,
    # since every later step reads spot/dte/strikes from `chain`). ----
    try:
        chain, mode = get_option_chain(symbol)
        spot = chain["spot"]
        dte = chain["days_to_expiry"]
    except Exception:
        logger.exception("get_option_chain failed for symbol=%s; aborting analysis", symbol)
        return metrics, "unavailable"

    # ---- Step 4: enrich each leg with its own market IV ----
    try:
        enriched_legs = [_enrich_leg_with_iv(leg, chain) for leg in legs]
    except Exception:
        logger.exception("Leg IV enrichment failed entirely; using raw legs")
        enriched_legs = legs

    # ---- Step 5: per-leg Black-Scholes Greeks ----
    try:
        legs_with_greeks = _compute_leg_greeks(spot, dte, enriched_legs)
        metrics["legs"] = legs_with_greeks
        metrics["greeks_per_leg"] = [leg.get("greeks") for leg in legs_with_greeks]
    except Exception:
        logger.exception("Greeks computation step failed entirely")
        legs_with_greeks = enriched_legs  # keep going with un-Greeked legs

    # ---- Step 6: portfolio-level Greeks (quantity & sign-weighted sum) ----
    try:
        portfolio = portfolio_greeks.aggregate(legs_with_greeks)
        metrics["portfolio_greeks"] = portfolio
    except Exception:
        logger.exception("Portfolio greeks aggregation failed")
        # leave the zeroed default from _safe_default_metrics()

    # ---- Steps 7-8: build the payoff curve ----
    # The payoff curve needs each leg's CURRENT theoretical value (its
    # Black-Scholes price right now) as the "entry price" reference point,
    # so that the curve correctly shows profit/loss *from here* rather
    # than from some other cost basis.
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
    except Exception:
        logger.exception("Payoff curve computation failed")

    # ---- Step 9: breakevens (curve zero-crossings) ----
    breakevens: list[float] = []
    try:
        breakevens = payoff.find_breakevens(curve)
        metrics["risk_metrics"]["breakevens"] = breakevens
    except Exception:
        logger.exception("Breakeven detection failed")

    # ---- Step 10: max profit / max loss from the curve's extremes ----
    try:
        profit_loss = payoff.compute_max_profit_loss(curve)
        metrics["risk_metrics"]["max_profit"] = profit_loss.get("max_profit")
        metrics["risk_metrics"]["max_loss"] = profit_loss.get("max_loss")
    except Exception:
        logger.exception("Max profit/loss computation failed")

    # ---- Step 11: probability of profit (PoP) ----
    # Single-leg strategies (e.g. one naked call) use a closed-form
    # lognormal-distribution calculation around one breakeven.
    # Multi-leg "spread" strategies (e.g. iron condor, two breakevens)
    # need the spread-aware version that integrates probability mass
    # between/outside multiple breakeven points. We branch on leg count
    # as the simplest reliable signal for which shape we're dealing with.
   # ---- Step 11: probability of profit (PoP) ----
    try:
        if len(legs_with_greeks) <= 1:
            pop = probability.for_single_leg(
                spot, breakevens, dte, RISK_FREE_RATE,
                legs_with_greeks[0].get("iv", chain.get("current_iv", 0.15)) if legs_with_greeks else chain.get("current_iv", 0.15),
            )
        else:
            pop = probability.for_spread(spot, breakevens, dte, RISK_FREE_RATE, chain.get("current_iv", 0.15))
        metrics["risk_metrics"]["probability_of_profit"] = float(pop)
    except Exception:
        logger.exception("Probability of profit computation failed")

    # ---- Step 12: margin requirement estimate ----
    try:
        margin_info = margin.estimate_margin(legs_with_greeks, spot)
        metrics["risk_metrics"]["margin_required"] = margin_info.get("estimated_margin", 0.0)
    except Exception:
        logger.exception("Margin estimation failed")

    # ---- Steps 13-14: liquidity, per-leg then aggregated ----
    try:
        leg_liquidity_scores = []
        for leg in legs_with_greeks:
            try:
                strike = leg["strike"]
                option_type = leg["option_type"]
                chain_row = next(
                    (s for s in chain.get("strikes", []) if s.get("strike") == strike),
                    None,
                )
                if chain_row is None:
                    leg_liquidity_scores.append(None)
                    continue

                # Safely pull the nested dictionary ("call" or "put")
                opt_data = chain_row.get(option_type, {})
                bid = opt_data.get("bid")
                ask = opt_data.get("ask")
                oi = opt_data.get("oi")
                volume = opt_data.get("volume")

                leg_liq = liquidity.compute_liquidity_score(oi, bid, ask, volume)
                leg_liquidity_scores.append(leg_liq)
            except Exception:
                logger.exception("Per-leg liquidity computation failed for leg=%s", leg)
                leg_liquidity_scores.append(None)

        valid_scores = [s for s in leg_liquidity_scores if s is not None]
        if valid_scores:
            strategy_liq = liquidity.strategy_liquidity(valid_scores)
            metrics["liquidity"] = strategy_liq
    except Exception:
        logger.exception("Liquidity computation failed entirely")

    # ---- Step 15: expected move, from the ATM straddle price ----
    try:
        atm_call_price, atm_put_price = _find_atm_strike_prices(chain, spot)
        if atm_call_price is not None and atm_put_price is not None:
            expected = expected_move.from_straddle(atm_call_price, atm_put_price, spot)
            metrics["expected_move_pct"] = expected.get("expected_move_pct")
        else:
            logger.info("ATM call/put prices unavailable; skipping expected move calc")
    except Exception:
        logger.exception("Expected move computation failed")

    # ---- Step 16: IV rank / regime classification ----
    # IV rank tells you where today's IV sits relative to its own
    # 52-week range (0 = lowest IV in a year, 100 = highest). This is
    # what assumption_checker.py later reads to judge "is this actually
    # a high-IV environment for THIS underlying" — a flat 20% IV might be
    # "high" for a normally-sleepy index and "low" for a volatile one,
    # so comparing to the symbol's own history (not an absolute number)
    # is the financially meaningful way to classify it.
    # ---- Step 16: IV rank / regime classification ----
    try:
        rank = compute_iv_rank(
            chain["current_iv"], chain["iv_52w_high"], chain["iv_52w_low"]
        )
        metrics["iv_rank"] = float(rank)
    except Exception:
        logger.exception("IV rank computation failed")

    return metrics, mode