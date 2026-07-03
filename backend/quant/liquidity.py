"""
liquidity.py — Options liquidity scoring for NSE options strikes.

─────────────────────────────────────────────────────────────────────
WHY LIQUIDITY MATTERS
─────────────────────────────────────────────────────────────────────
Black-Scholes gives you the THEORETICAL price of an option. But when
you actually trade, you pay the ASK price (to buy) and receive the BID
price (to sell). The bid-ask spread is the immediate, guaranteed cost
of entering a position — a tax you pay before the market even moves.

Example:
    Theoretical BS price: ₹100
    Bid: ₹95, Ask: ₹105   → spread = ₹10 (10%)
    If you buy at 105 and immediately sell at 95, you've lost ₹10/unit
    before Nifty moves at all. On 50 lots: ₹500 per round trip.

For illiquid OTM strikes (especially in BankNifty far-wings), spreads
can be 20-30%, making them economically unviable for most retail traders.

─────────────────────────────────────────────────────────────────────
SCORING METHODOLOGY
─────────────────────────────────────────────────────────────────────
Three components, weighted by their importance to actual tradability:

1. BID-ASK SPREAD SCORE (50% weight) — most important signal
   Formula: max(0, 100 - spread_pct × 10)
   - spread_pct = (ask - bid) / mid × 100
   - At 0% spread: score = 100 (perfect, no spread cost)
   - At 5% spread: score = 50  (moderate, half marks)
   - At 10%+ spread: score = 0  (poor, execution heavily penalised)

2. OPEN INTEREST SCORE (30% weight) — measures existing market participation
   Formula: min(100, OI / 1000) × 100
   - OI ≥ 100,000: score = 100 (deep liquidity, many participants)
   - OI = 50,000: score = 50  (moderate)
   - OI < 10,000: score < 10  (low liquidity, wide spreads likely)

3. VOLUME SCORE (20% weight) — measures today's trading activity
   Formula: min(100, volume / 500) × 100
   - Volume ≥ 50,000: score = 100
   - Volume = 25,000: score = 50
   - Volume < 5,000: score low (stale book, not actively traded today)

Overall: weighted sum of the three components.
Labels: ≥70 → Good, ≥40 → Moderate, <40 → Poor

─────────────────────────────────────────────────────────────────────
"""

import logging

logger = logging.getLogger(__name__)


def compute_liquidity_score(
    oi: int,
    bid: float,
    ask: float,
    volume: int
) -> dict:
    """
    Compute a liquidity score (0-100) for a single options strike.

    Parameters
    ----------
    oi     : int   — Open Interest (number of open contracts)
    bid    : float — best bid price in the market (index points)
    ask    : float — best ask price in the market (index points)
    volume : int   — total contracts traded today

    Returns
    -------
    dict:
        score      : float — overall liquidity score 0-100
        label      : str   — "Good", "Moderate", or "Poor — wide spreads may affect execution"
        spread_pct : float — percentage bid-ask spread (lower is better)
        oi         : int   — open interest passed in
        volume     : int   — volume passed in
        component_scores: dict — breakdown of each component for UI display
    """
    # ── Input validation ──────────────────────────────────────────────────────
    if bid < 0 or ask < 0:
        logger.warning("Negative bid/ask: bid=%.2f, ask=%.2f — clamping to 0", bid, ask)
        bid = max(0.0, bid)
        ask = max(0.0, ask)

    if ask < bid:
        logger.warning("ask (%.2f) < bid (%.2f) — swapping (crossed market)", ask, bid)
        bid, ask = ask, bid

    if oi < 0:
        logger.warning("Negative OI=%d — clamping to 0", oi)
        oi = 0

    if volume < 0:
        logger.warning("Negative volume=%d — clamping to 0", volume)
        volume = 0

    # ── Component 1: Bid-Ask Spread Score (weight: 50%) ──────────────────────
    # Mid price = (bid + ask) / 2
    # Spread = ask - bid
    # Spread percentage = (ask - bid) / mid × 100
    # Score = max(0, 100 - spread_pct × 10)
    #   → 0% spread = 100 score (no execution cost)
    #   → 10%+ spread = 0 score (severely penalised)
    mid = (bid + ask) / 2.0

    if mid <= 0:
        # Zero or negative mid — happens with zero bids (deeply OTM or no market)
        spread_pct = 100.0   # Penalise as maximally illiquid
        spread_score = 0.0
        logger.warning("Mid price = %.2f (zero or negative), spread_score = 0", mid)
    else:
        spread_pct = ((ask - bid) / mid) * 100.0
        spread_score = max(0.0, 100.0 - spread_pct * 10.0)

    # ── Component 2: Open Interest Score (weight: 30%) ────────────────────────
    # OI represents how many contracts are currently open in the market.
    # Higher OI = more participants = typically tighter spreads.
    # Formula: min(100, OI / 1000) — normalised so OI ≥ 100,000 → full score
    #
    # Why 1000 as denominator? Nifty's heavily-traded strikes (ATM ± 2 strikes)
    # typically have OI in the range of 1M-5M contracts. Our formula:
    #   OI=100,000 → 100k/1000 = 100 (max score)
    # This means any OI above 100k is considered "deep" liquidity.
    oi_score = min(100.0, oi / 1000.0)

    # ── Component 3: Volume Score (weight: 20%) ───────────────────────────────
    # Daily volume shows how actively this strike is being traded TODAY.
    # Low volume can mean stale quotes (bid/ask not updated, wide spreads).
    # Formula: min(100, volume / 500) — normalised so volume ≥ 50,000 → full score
    volume_score = min(100.0, volume / 500.0)

    # ── Weighted total score ──────────────────────────────────────────────────
    total_score = (
        spread_score  * 0.50 +   # spread matters most
        oi_score      * 0.30 +   # OI is a market depth indicator
        volume_score  * 0.20     # volume shows today's activity
    )

    total_score = round(max(0.0, min(100.0, total_score)), 2)

    # ── Label classification ──────────────────────────────────────────────────
    if total_score >= 70:
        label = "Good"
    elif total_score >= 40:
        label = "Moderate"
    else:
        label = "Poor — wide spreads may affect execution"

    return {
        "score":      total_score,
        "label":      label,
        "spread_pct": round(spread_pct, 2),
        "oi":         oi,
        "volume":     volume,
        "component_scores": {
            "spread_score":  round(spread_score,  2),
            "oi_score":      round(oi_score,       2),
            "volume_score":  round(volume_score,   2),
        },
    }


def strategy_liquidity(legs_liquidity: list[dict]) -> dict:
    """
    Compute overall strategy liquidity from individual leg liquidity scores.

    Uses the WEAKEST LINK principle: a strategy is only as liquid as its
    least-liquid leg. If one leg has a 20% bid-ask spread, the entire
    strategy is difficult to execute efficiently regardless of how liquid
    the other legs are.

    Parameters
    ----------
    legs_liquidity : list of dicts — each from compute_liquidity_score()

    Returns
    -------
    dict: Matches the LiquidityInfo Pydantic model strictly.
    """
    if not legs_liquidity:
        logger.warning("strategy_liquidity called with empty legs list")
        return {
            "score": 0.0,
            "label": "unknown",
            "spread_pct": 0.0,
        }

    # Find the leg with the lowest score (weakest link)
    scores = [leg.get("score", 0.0) for leg in legs_liquidity]
    min_score = min(scores)

    # The strategy's label is determined by the worst leg's score
    if min_score >= 70:
        label = "Good"
    elif min_score >= 40:
        label = "Moderate"
    else:
        label = "Poor — wide spreads may affect execution"

    # Calculate average spread percentage across all legs for overall strategy health
    spreads = [leg.get("spread_pct", 0.0) for leg in legs_liquidity]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0.0

    return {
        "score": round(min_score, 2),
        "label": label,
        "spread_pct": round(avg_spread, 2),
    }


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    # ATM option — tight spread, high OI and volume (should be "Good")
    print("=" * 60)
    print("Test 1: Liquid ATM strike (tight spread, high OI/volume)")
    r1 = compute_liquidity_score(oi=500_000, bid=398.0, ask=402.0, volume=25_000)
    print(json.dumps(r1, indent=2))
    # Expected: Good score, spread ~1%

    # Far OTM option — wide spread, low OI (should be "Poor")
    print("=" * 60)
    print("Test 2: Illiquid far OTM strike")
    r2 = compute_liquidity_score(oi=5_000, bid=5.0, ask=15.0, volume=100)
    print(json.dumps(r2, indent=2))
    # Expected: Poor score, spread ~100%

    # Strategy with mixed liquidity
    print("=" * 60)
    print("Test 3: Strategy with mixed leg liquidity")
    r3 = strategy_liquidity([r1, r2])
    print(json.dumps(r3, indent=2))
    # Expected: strategy score = min(r1, r2) = r2's poor score