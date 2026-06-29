"""
expected_move.py — Market-implied expected move for an underlying.

─────────────────────────────────────────────────────────────────────
WHAT IS EXPECTED MOVE?
─────────────────────────────────────────────────────────────────────
The options market, through pricing, implicitly reveals how much the
underlying is expected to move by expiry. This is the market's collective
estimate — not a prediction, but the PRICED-IN uncertainty.

Method 1 — ATM Straddle Price (preferred):
    The ATM straddle (long call + long put at the same ATM strike) profits
    if the underlying moves MORE than the combined premium in either direction.
    The straddle price IS the market's expected move. This is not a model —
    it's what you can observe directly from option prices.

    Expected Move = ATM Call Price + ATM Put Price

Method 2 — From IV (when straddle prices unavailable):
    Uses the Black-Scholes relationship between IV and expected move.

    Expected Move = Spot × IV × √(T/365)

    This formula comes from the lognormal distribution: the standard deviation
    of a lognormally distributed asset over T days is S × σ × √T (in years).

─────────────────────────────────────────────────────────────────────
INTERPRETATION
─────────────────────────────────────────────────────────────────────
The result defines the ±1 standard deviation range.

If Nifty is at 19000 and expected move = ±400 pts:
    - Market expects Nifty to close between 18600 and 19400 at expiry
    - With ~68% probability (properties of normal distribution)
    - Selling an OTM strangle outside this range has ~68% chance of full profit

This is the same "expected move" shown on platforms like Tastyworks, OptionStrat,
and Sensibull's Nifty options page.
"""

import math
import logging

logger = logging.getLogger(__name__)


def from_straddle(
    atm_call_price: float,
    atm_put_price: float,
    spot: float
) -> dict:
    """
    Compute expected move from ATM straddle price.

    The combined price of ATM call + ATM put equals the market's expected
    1-standard-deviation move by expiry. This is the most direct measure
    because it reads straight from observed market prices.

    Parameters
    ----------
    atm_call_price : float — current price of the at-the-money call (index pts)
    atm_put_price  : float — current price of the at-the-money put (index pts)
    spot           : float — current underlying price (e.g. Nifty at 19000)

    Returns
    -------
    dict:
        expected_move_points : float — ±move in index points
        expected_move_pct    : float — ±move as percentage of spot
        upper_bound          : float — spot + expected_move (upside target)
        lower_bound          : float — spot - expected_move (downside target)
        interpretation       : str   — human-readable summary
    """
    if spot <= 0:
        logger.error("from_straddle: spot=%s is invalid (<= 0)", spot)
        return _empty_result()

    if atm_call_price < 0 or atm_put_price < 0:
        logger.error(
            "from_straddle: negative option prices (call=%.2f, put=%.2f)",
            atm_call_price, atm_put_price
        )
        return _empty_result()

    # ── Core formula ──────────────────────────────────────────────────────────
    # The straddle price IS the expected move. No model assumptions here —
    # this is simply the price you would pay to buy both options.
    # If you pay 400 for the straddle, you break even if Nifty moves ±400.
    expected_move_points = atm_call_price + atm_put_price
    expected_move_pct    = (expected_move_points / spot) * 100.0

    upper_bound = spot + expected_move_points
    lower_bound = spot - expected_move_points

    interpretation = (
        f"Market prices in ±{expected_move_points:.0f} pts "
        f"(±{expected_move_pct:.1f}%) move by expiry. "
        f"Expected range: {lower_bound:.0f} – {upper_bound:.0f}."
    )

    return {
        "expected_move_points": round(expected_move_points, 2),
        "expected_move_pct":    round(expected_move_pct, 2),
        "upper_bound":          round(upper_bound, 2),
        "lower_bound":          round(lower_bound, 2),
        "interpretation":       interpretation,
        "source":               "straddle",
    }


def from_iv(spot: float, iv: float, T_days: int) -> dict:
    """
    Compute expected move from implied volatility.

    Alternative when you don't have live option prices, or as a cross-check
    against the straddle method.

    Formula: Expected Move = Spot × IV × √(T_days / 365)

    Derivation:
    Under lognormal assumptions (Black-Scholes world), the underlying's
    1-year standard deviation is S × σ. Over T days, scaling by √(T/365)
    gives the T-day standard deviation. This is the ±1σ expected range.

    Note: The straddle method gives a slightly different result because of
    the "smile" (options aren't priced purely lognormally). In practice,
    the straddle price slightly underestimates the expected move because of
    put-call parity adjustments. The IV method is a cleaner theoretical formula.

    Parameters
    ----------
    spot   : float — current underlying price
    iv     : float — implied volatility as decimal (0.15 = 15%)
    T_days : int   — calendar days to expiry

    Returns
    -------
    dict — same structure as from_straddle()
    """
    if spot <= 0:
        logger.error("from_iv: spot=%s is invalid", spot)
        return _empty_result()

    if iv <= 0:
        logger.error("from_iv: iv=%s is invalid (<= 0)", iv)
        return _empty_result()

    if T_days <= 0:
        logger.warning("from_iv: T_days=%s <= 0. Expected move = 0.", T_days)
        return {
            "expected_move_points": 0.0,
            "expected_move_pct":    0.0,
            "upper_bound":          spot,
            "lower_bound":          spot,
            "interpretation":       "Option has expired (T=0). No expected move.",
            "source":               "iv",
        }

    # ── Core formula ──────────────────────────────────────────────────────────
    # S × σ × √(T/365) is the 1-standard-deviation move over T calendar days.
    # At T=365, this equals S × σ (the full annualised vol).
    # At T=30, this is S × σ × √(30/365) ≈ S × σ × 0.286 (about 28.6% of annual vol)
    T_years = T_days / 365.0
    expected_move_points = spot * iv * math.sqrt(T_years)
    expected_move_pct    = (expected_move_points / spot) * 100.0

    upper_bound = spot + expected_move_points
    lower_bound = spot - expected_move_points

    interpretation = (
        f"Market prices in ±{expected_move_points:.0f} pts "
        f"(±{expected_move_pct:.1f}%) move by expiry. "
        f"Expected range: {lower_bound:.0f} – {upper_bound:.0f}. "
        f"(Based on {iv*100:.1f}% IV over {T_days} days)"
    )

    return {
        "expected_move_points": round(expected_move_points, 2),
        "expected_move_pct":    round(expected_move_pct, 2),
        "upper_bound":          round(upper_bound, 2),
        "lower_bound":          round(lower_bound, 2),
        "interpretation":       interpretation,
        "source":               "iv_formula",
    }


def _empty_result() -> dict:
    """Return a safe zero result on invalid inputs."""
    return {
        "expected_move_points": 0.0,
        "expected_move_pct":    0.0,
        "upper_bound":          0.0,
        "lower_bound":          0.0,
        "interpretation":       "Unable to compute expected move — invalid inputs.",
        "source":               "error",
    }


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    # Use our BS output: ATM Nifty call=378.19, put ≈ similar (put-call parity)
    # For ATM: put ≈ call - S + K*e^(-rT) ≈ 378.19 - 19000 + 19000*e^(-0.065*30/365)
    import math as m
    atm_put_theoretical = 378.19 - 19000 + 19000 * m.exp(-0.065 * 30/365)
    print(f"Theoretical ATM put: {atm_put_theoretical:.2f}")

    r1 = from_straddle(atm_call_price=378.19, atm_put_price=atm_put_theoretical, spot=19000)
    print("Straddle method:")
    print(json.dumps(r1, indent=2))

    r2 = from_iv(spot=19000, iv=0.15, T_days=30)
    print("IV formula method:")
    print(json.dumps(r2, indent=2))

    # Cross-check: both should give similar expected_move_points (~350-400)
    print(f"Straddle EM: {r1['expected_move_points']:.1f}")
    print(f"IV formula EM: {r2['expected_move_points']:.1f}")