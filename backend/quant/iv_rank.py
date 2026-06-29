"""
iv_rank.py — Implied Volatility rank, percentile, and regime classification.

─────────────────────────────────────────────────────────────────────
WHAT IS IV RANK AND WHY DOES IT MATTER?
─────────────────────────────────────────────────────────────────────
Implied Volatility (IV) itself is hard to interpret in isolation.
An IV of 15% for Nifty could be "low" in 2020 (when it was 40%) but
"high" in 2023 (when it was typically 10-12%). Context is everything.

IV RANK answers: "Where in the past year's IV range does today's IV sit?"
    Formula: (current IV - 52w low) / (52w high - 52w low) × 100
    Result: 0 to 100 scale

IV PERCENTILE answers: "On what % of past days was IV lower than today?"
    Formula: count(historical_iv < current_iv) / count(all_days) × 100
    More accurate but requires time series data.

─────────────────────────────────────────────────────────────────────
TRADING IMPLICATIONS (for UI narrative, not recommendations)
─────────────────────────────────────────────────────────────────────
IV Rank > 60 ("High IV"):
    Options are EXPENSIVE relative to historical norms.
    Premium sellers have an edge: if IV mean-reverts, sold options
    decay faster than expected. Strategies: iron condors, short strangles,
    covered calls.

IV Rank < 40 ("Low IV"):
    Options are CHEAP relative to historical norms.
    Premium buyers have an edge: buying volatility is inexpensive.
    Strategies: long straddles, long strangles, long calls/puts.

IV Rank 40-60 ("Neutral"):
    No clear edge from IV alone. Use other analysis (trend, earnings, etc.).

─────────────────────────────────────────────────────────────────────
NOTE: India VIX (India's fear gauge) is the best proxy for Nifty IV.
In production, pull India VIX from NSE's website to populate these values.
─────────────────────────────────────────────────────────────────────
"""

import logging
from typing import Union

logger = logging.getLogger(__name__)


def compute_iv_rank(
    current_iv: float,
    iv_52w_high: float,
    iv_52w_low: float
) -> float:
    """
    Compute IV Rank: where current IV sits within its 52-week range.

    Formula: IV_Rank = (current - low) / (high - low) × 100

    Returns 0–100 scale:
        0   = current IV is at its 52-week low
        100 = current IV is at its 52-week high
        50  = current IV is exactly at the midpoint of its 52-week range

    Edge case: if high == low (IV has not changed in a year), returns 50.0
    (neutral — no information to act on).

    Parameters
    ----------
    current_iv  : float — today's implied volatility (as decimal, e.g. 0.15)
    iv_52w_high : float — highest IV seen in past 52 weeks
    iv_52w_low  : float — lowest IV seen in past 52 weeks

    Returns
    -------
    float — IV rank on 0–100 scale (rounded to 2dp)
    """
    # ── Validation ────────────────────────────────────────────────────────────
    if iv_52w_high < iv_52w_low:
        logger.warning(
            "iv_52w_high (%.4f) < iv_52w_low (%.4f) — swapping values",
            iv_52w_high, iv_52w_low
        )
        iv_52w_high, iv_52w_low = iv_52w_low, iv_52w_high

    # ── Edge case: no IV variation over the year ──────────────────────────────
    if abs(iv_52w_high - iv_52w_low) < 1e-10:
        logger.warning(
            "iv_52w_high == iv_52w_low (%.4f). No IV range available. Returning 50.0.",
            iv_52w_high
        )
        return 50.0

    # ── Core IV Rank formula ──────────────────────────────────────────────────
    iv_rank = (current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low) * 100.0

    # Clamp to [0, 100] — current IV could technically be outside the 52w range
    # if computed using a lagged data source (e.g. close-of-day IV vs intraday spike)
    iv_rank = max(0.0, min(100.0, iv_rank))

    return round(iv_rank, 2)


def compute_iv_percentile(
    current_iv: float,
    historical_ivs: list[float]
) -> float:
    """
    Compute IV Percentile: percentage of historical observations BELOW current IV.

    This is more statistically rigorous than IV Rank because:
    - IV Rank is distorted by extreme outliers (one spike can compress the rank)
    - IV Percentile looks at the entire distribution, not just high/low

    Example: if Nifty IV was below 15% on 70 of the past 252 trading days,
    and current IV is 15%, then IV Percentile = 70/252 × 100 ≈ 27.8%

    Parameters
    ----------
    current_iv      : float      — today's implied volatility (as decimal)
    historical_ivs  : list[float] — ordered list of historical IV values
                                    (ideally 252 days = 1 trading year)

    Returns
    -------
    float — percentile on 0–100 scale (rounded to 2dp)
    Returns 0.0 if historical_ivs is empty.
    """
    if not historical_ivs:
        logger.warning("compute_iv_percentile called with empty historical_ivs. Returning 0.0.")
        return 0.0

    # Count how many historical observations are STRICTLY below current IV
    count_below = sum(1 for iv in historical_ivs if iv < current_iv)

    # Percentage of days where IV was lower
    percentile = (count_below / len(historical_ivs)) * 100.0

    return round(percentile, 2)


def classify_iv_regime(iv_rank: float) -> str:
    """
    Classify current IV environment based on IV rank.

    Thresholds:
        >= 60 → "high"    (options expensive, sellers have edge)
        <= 40 → "low"     (options cheap, buyers have edge)
        else  → "neutral" (no clear IV-based edge)

    Parameters
    ----------
    iv_rank : float — IV rank on 0–100 scale

    Returns
    -------
    str — "high", "low", or "neutral"
    """
    if iv_rank >= 60:
        return "high"
    elif iv_rank <= 40:
        return "low"
    else:
        return "neutral"


def full_iv_analysis(
    current_iv: float,
    iv_52w_high: float,
    iv_52w_low: float,
    historical_ivs: list[float] = None
) -> dict:
    """
    Convenience function that runs all IV analyses and returns a combined result.

    Parameters
    ----------
    current_iv     : current implied volatility (decimal)
    iv_52w_high    : 52-week high IV (decimal)
    iv_52w_low     : 52-week low IV (decimal)
    historical_ivs : optional list of daily IV values for percentile calculation

    Returns
    -------
    dict:
        iv_rank      : float — 0-100 rank
        iv_percentile: float — 0-100 percentile (0.0 if no history supplied)
        regime       : str   — "high", "low", or "neutral"
        current_iv_pct: float — current IV as percentage for display (e.g. 15.0 for 0.15)
    """
    if historical_ivs is None:
        historical_ivs = []

    rank = compute_iv_rank(current_iv, iv_52w_high, iv_52w_low)
    percentile = compute_iv_percentile(current_iv, historical_ivs)
    regime = classify_iv_regime(rank)

    return {
        "iv_rank": rank,
        "iv_percentile": percentile,
        "regime": regime,
        "current_iv_pct": round(current_iv * 100, 2),   # convert 0.15 → 15.0 for display
    }


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    # Scenario 1: India VIX at 18 (in a 12-30 range over the year)
    # IV Rank = (18 - 12) / (30 - 12) × 100 = 33.3 → "low"
    r1 = full_iv_analysis(
        current_iv=0.18,
        iv_52w_high=0.30,
        iv_52w_low=0.12,
        historical_ivs=[0.12, 0.14, 0.15, 0.18, 0.20, 0.25, 0.30]
    )
    print("Scenario 1 (VIX at 18, range 12-30):", json.dumps(r1))

    # Scenario 2: IV at 52-week high → rank should be 100
    r2 = compute_iv_rank(current_iv=0.35, iv_52w_high=0.35, iv_52w_low=0.10)
    print(f"At 52w high: IV rank = {r2} (expect 100.0)")

    # Scenario 3: High == low edge case
    r3 = compute_iv_rank(current_iv=0.15, iv_52w_high=0.15, iv_52w_low=0.15)
    print(f"High==Low edge case: IV rank = {r3} (expect 50.0)")

    # Scenario 4: Regime classification
    for rank, expected in [(75, "high"), (50, "neutral"), (25, "low")]:
        regime = classify_iv_regime(rank)
        print(f"IV rank {rank} → regime: {regime} (expect: {expected})")