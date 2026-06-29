"""
margin.py — Simplified SPAN margin estimation for NSE options strategies.

─────────────────────────────────────────────────────────────────────
IMPORTANT DISCLAIMER (always display this to users)
─────────────────────────────────────────────────────────────────────
SPAN (Standard Portfolio Analysis of Risk) is the actual margin
methodology used by NSE. It runs a complex scenario simulation across
16 price and volatility scenarios and takes the worst-case loss as the
margin requirement. It also considers cross-margining, portfolio netting,
and intra-day margin calls.

This module provides ESTIMATES ONLY using simplified heuristic rules.
The actual margin required by your broker may differ significantly,
especially for:
  - Complex multi-leg strategies
  - Near-expiry positions (margin spikes near expiry)
  - High-volatility periods (NSE raises SPAN margins during volatile markets)
  - Broker-specific additional "exposure margin" requirements

Always verify margin requirements with your broker before placing trades.

─────────────────────────────────────────────────────────────────────
MARGIN RULES USED (simplified)
─────────────────────────────────────────────────────────────────────
1. LONG OPTIONS ONLY:
   Margin = premium paid (no additional margin required)
   Rationale: your maximum loss is the premium; the exchange already has it.

2. DEFINED-RISK STRATEGIES (vertical spreads, iron condors, etc.):
   Margin ≈ maximum possible loss of the spread
   Rationale: the long leg acts as a hedge, capping the worst case.
   NSE recognises this and grants margin benefit for defined-risk spreads.

3. NAKED SHORT OPTION (undefined risk):
   Margin ≈ 12% of notional value (spot × lot_size × quantity)
   Rationale: NSE's SPAN typically requires margin in the range of
   10-15% of notional for ATM short options. 12% is a mid-range estimate.

4. NAKED SHORT STRADDLE / STRANGLE:
   Margin ≈ higher of (short call margin, short put margin) + 50% of other
   Rationale: Simplified portfolio margining — the two positions partially
   offset each other's risk (if spot rises, put losses, call gains).

─────────────────────────────────────────────────────────────────────
"""

import logging
from quant.payoff import compute_payoff_curve, compute_max_profit_loss

logger = logging.getLogger(__name__)

# NSE simplified naked short margin rate (12% of notional, conservative estimate)
NAKED_SHORT_MARGIN_RATE = 0.12

# Standard disclaimer — always return this to the UI
MARGIN_DISCLAIMER = (
    "Estimated margin only. Actual SPAN margin may differ based on volatility, "
    "time to expiry, and broker policies. Always verify with your broker before trading."
)


def _classify_strategy(legs: list[dict]) -> str:
    """
    Classify strategy type for margin calculation purposes.

    Returns one of:
        "long_only"       — all positions are long (bought)
        "defined_risk"    — has both short and long legs (spread, condor)
        "naked_short"     — short position(s) with no hedging long leg
        "mixed_undefined" — complex combination with undefined risk
    """
    has_long  = any(leg.get("side", "").lower() == "buy"  for leg in legs)
    has_short = any(leg.get("side", "").lower() == "sell" for leg in legs)

    if has_short and has_long:
        return "defined_risk"
    elif has_short and not has_long:
        return "naked_short"
    elif has_long and not has_short:
        return "long_only"
    else:
        return "long_only"  # default


def estimate_margin(legs: list[dict], spot: float) -> dict:
    """
    Estimate margin required to place this options strategy.

    Parameters
    ----------
    legs : list of leg dicts, each containing:
           "side"        : "buy" or "sell"
           "option_type" : "call" or "put"
           "quantity"    : int — number of lots
           "lot_size"    : int — shares per lot
           "entry_price" : float — premium in index points
           "strike"      : float — for payoff curve computation
    spot : float — current underlying spot price

    Returns
    -------
    dict:
        estimated_margin : float  — estimated total margin in ₹
        basis            : str    — explanation of how margin was calculated
        is_defined_risk  : bool   — True if max loss is known and capped
        disclaimer       : str    — always shown to user
    """
    if not legs:
        return {
            "estimated_margin": 0.0,
            "basis": "No legs provided.",
            "is_defined_risk": True,
            "disclaimer": MARGIN_DISCLAIMER,
        }

    if spot <= 0:
        logger.error("estimate_margin: invalid spot=%s", spot)
        return {
            "estimated_margin": 0.0,
            "basis": "Invalid spot price.",
            "is_defined_risk": False,
            "disclaimer": MARGIN_DISCLAIMER,
        }

    strategy_class = _classify_strategy(legs)
    logger.debug("Strategy class: %s", strategy_class)

    # ── CASE 1: Long-only positions ───────────────────────────────────────────
    # For long options, margin = total premium paid (already in your account).
    # No additional margin is charged by the exchange.
    if strategy_class == "long_only":
        total_premium = 0.0
        for leg in legs:
            try:
                premium  = float(leg.get("entry_price", 0.0))
                quantity = int(leg.get("quantity", 1))
                lot_size = int(leg.get("lot_size", 50))
                # Total premium paid = price × lots × lot_size × rupee_value_per_point
                # Since lot_size already converts points to rupee notional:
                total_premium += premium * quantity * lot_size
            except (TypeError, ValueError) as e:
                logger.error("Error processing leg in margin calc: %s", e)

        return {
            "estimated_margin": round(total_premium, 2),
            "basis": "Long options only: margin = total premium paid (max loss is the premium).",
            "is_defined_risk": True,
            "disclaimer": MARGIN_DISCLAIMER,
        }

    # ── CASE 2: Defined-risk strategy (has both long and short legs) ──────────
    # Margin = maximum possible loss of the strategy.
    # We compute this from the payoff curve (the most reliable method).
    if strategy_class == "defined_risk":
        try:
            curve = compute_payoff_curve(legs, spot, num_points=200)
            result = compute_max_profit_loss(curve)
            max_loss = result.get("max_loss", 0.0)

            # If max_loss is the "unlimited" sentinel, fall through to naked short calc
            if max_loss <= -999_000_000:
                logger.warning(
                    "Defined-risk strategy shows unlimited loss — reclassifying as naked."
                )
                strategy_class = "naked_short"
            else:
                # max_loss is negative (a loss), so take abs for margin amount
                margin = abs(max_loss)
                return {
                    "estimated_margin": round(margin, 2),
                    "basis": (
                        f"Defined-risk strategy: margin = maximum possible loss = ₹{margin:,.0f}. "
                        "The long leg(s) cap the downside, so NSE grants margin offset."
                    ),
                    "is_defined_risk": True,
                    "disclaimer": MARGIN_DISCLAIMER,
                }
        except Exception as exc:
            logger.error("Error computing payoff curve for margin: %s", exc)
            # Fall through to naked short estimate

    # ── CASE 3: Naked short (or fallback from failed defined-risk) ────────────
    # Margin ≈ 12% of notional for each short leg.
    # Notional = spot × quantity × lot_size (total underlying value controlled)
    short_legs = [leg for leg in legs if leg.get("side", "").lower() == "sell"]
    total_margin = 0.0
    margin_parts = []

    for leg in short_legs:
        try:
            quantity = int(leg.get("quantity", 1))
            lot_size = int(leg.get("lot_size", 50))
            # Notional value = spot price × number of units controlled
            notional = spot * quantity * lot_size
            leg_margin = notional * NAKED_SHORT_MARGIN_RATE
            total_margin += leg_margin
            margin_parts.append(
                f"{leg.get('side','sell')} {leg.get('option_type','?')} "
                f"K={leg.get('strike','?')}: ₹{leg_margin:,.0f}"
            )
        except (TypeError, ValueError) as e:
            logger.error("Error computing naked margin for leg: %s", e)

    # For straddles/strangles (short call + short put), NSE gives partial offset:
    # typically margin = max(call margin, put margin) + 50% of the smaller
    # We implement this if there are exactly 2 naked short legs
    if len(short_legs) == 2:
        leg_margins = []
        for leg in short_legs:
            try:
                notional = spot * int(leg.get("quantity", 1)) * int(leg.get("lot_size", 50))
                leg_margins.append(notional * NAKED_SHORT_MARGIN_RATE)
            except (TypeError, ValueError):
                continue

        if len(leg_margins) == 2:
            # Portfolio margin benefit: max + 50% of smaller
            bigger  = max(leg_margins)
            smaller = min(leg_margins)
            total_margin = bigger + 0.5 * smaller
            basis = (
                f"Naked short straddle/strangle: margin = max leg (₹{bigger:,.0f}) "
                f"+ 50% of smaller leg (₹{smaller * 0.5:,.0f}) = ₹{total_margin:,.0f}. "
                f"Based on {NAKED_SHORT_MARGIN_RATE*100:.0f}% of notional per leg."
            )
        else:
            basis = f"Naked short: {NAKED_SHORT_MARGIN_RATE*100:.0f}% of notional. Parts: {'; '.join(margin_parts)}"
    else:
        basis = (
            f"Naked/undefined-risk short: {NAKED_SHORT_MARGIN_RATE*100:.0f}% of notional "
            f"per short leg. {'; '.join(margin_parts)}"
        )

    return {
        "estimated_margin": round(total_margin, 2),
        "basis": basis,
        "is_defined_risk": False,
        "disclaimer": MARGIN_DISCLAIMER,
    }


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    sys.path.insert(0, ".")
    logging.basicConfig(level=logging.INFO)

    spot = 19000

    # Test 1: Long call (defined risk = premium paid)
    print("=" * 60)
    print("Test 1: Long call")
    r1 = estimate_margin(
        [{"side":"buy","option_type":"call","strike":19000,"quantity":1,"lot_size":50,"entry_price":400}],
        spot
    )
    print(json.dumps(r1, indent=2))
    # Expected: ₹20,000 (400 × 50)

    # Test 2: Iron condor (defined risk = max loss of the spread)
    print("=" * 60)
    print("Test 2: Iron condor")
    ic_legs = [
        {"side":"buy", "option_type":"put",  "strike":18500,"quantity":1,"lot_size":50,"entry_price":50},
        {"side":"sell","option_type":"put",  "strike":19000,"quantity":1,"lot_size":50,"entry_price":200},
        {"side":"sell","option_type":"call", "strike":19500,"quantity":1,"lot_size":50,"entry_price":200},
        {"side":"buy", "option_type":"call", "strike":20000,"quantity":1,"lot_size":50,"entry_price":50},
    ]
    r2 = estimate_margin(ic_legs, spot)
    print(json.dumps(r2, indent=2))

    # Test 3: Naked short call
    print("=" * 60)
    print("Test 3: Naked short call")
    r3 = estimate_margin(
        [{"side":"sell","option_type":"call","strike":19500,"quantity":1,"lot_size":50,"entry_price":200}],
        spot
    )
    print(json.dumps(r3, indent=2))
    # Expected: 12% × 19000 × 50 = ₹1,14,000