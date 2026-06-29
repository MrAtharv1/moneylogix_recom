"""
payoff.py — Strategy P&L at expiry across a range of underlying prices.

─────────────────────────────────────────────────────────────────────
WHAT THIS MODULE COMPUTES
─────────────────────────────────────────────────────────────────────
The payoff chart is the most fundamental options visualisation.
It shows: "At expiry, for every possible Nifty closing price, what is
my strategy's profit or loss?"

This is simpler than the stress test (stress_test.py), which uses
Black-Scholes mid-life repricing. Here, at expiry, option value equals
its INTRINSIC VALUE — no time value remains:

    Call intrinsic value = max(0, underlying_price - strike)
    Put  intrinsic value = max(0, strike - underlying_price)

────────────────────────────────────────────────────────────────────
SIGN CONVENTION
────────────────────────────────────────────────────────────────────
BUY  a call: you PAID a premium. You profit when intrinsic > premium.
SELL a call: you RECEIVED a premium. You profit when intrinsic = 0 (expires worthless).

P&L per leg at expiry:
    (intrinsic_value - entry_price) × quantity × lot_size × direction
    where direction = +1 for BUY, -1 for SELL

Examples:
    Buy  call, K=19000, entry=400, spot=19500 at expiry:
        intrinsic = max(0, 19500-19000) = 500
        P&L = (500 - 400) × 1 × 50 × (+1) = +₹5,000

    Sell put, K=19000, entry=300, spot=19200 at expiry (expires worthless):
        intrinsic = max(0, 19000-19200) = 0
        P&L = (0 - 300) × 1 × 50 × (-1) = +₹15,000 (premium kept)

─────────────────────────────────────────────────────────────────────
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Strategy direction multiplier
DIRECTION_SIGN = {"buy": 1, "sell": -1}


def _intrinsic_value(option_type: str, strike: float, underlying_price: float) -> float:
    """
    Compute option intrinsic value at expiry.

    For a call: intrinsic = max(0, underlying_price - strike)
        (you profit when underlying is above strike)
    For a put:  intrinsic = max(0, strike - underlying_price)
        (you profit when underlying is below strike)

    This is the "floor" value — an option can NEVER be worth less than
    its intrinsic value at expiry (arbitrage would prevent it).
    """
    opt = option_type.strip().lower()
    if opt == "call":
        return max(0.0, underlying_price - strike)
    elif opt == "put":
        return max(0.0, strike - underlying_price)
    else:
        logger.error("Unknown option_type '%s' in _intrinsic_value", option_type)
        return 0.0


def compute_payoff_curve(
    legs: list[dict],
    spot: float,
    num_points: int = 100
) -> list[dict]:
    """
    Compute strategy P&L at expiry across a range of underlying prices.

    Price range: spot × 0.90 to spot × 1.10 (±10% of current spot).
    This captures most realistic outcomes for index options.

    Parameters
    ----------
    legs       : list of leg dicts, each containing:
                    "strike"      : float  — option strike price
                    "option_type" : str    — "call" or "put"
                    "side"        : str    — "buy" or "sell"
                    "quantity"    : int    — number of lots
                    "lot_size"    : int    — shares per lot (e.g. 50 for Nifty)
                    "entry_price" : float  — premium paid/received (index points)
    spot       : float — current spot price (used to define the price range)
    num_points : int   — number of price points in the curve (default 100)

    Returns
    -------
    list of dicts: [{"price": float, "pnl": float}, ...]
        price: underlying price at expiry (in index points)
        pnl  : strategy total P&L in rupees (₹) at that price
    """
    if not legs:
        logger.warning("compute_payoff_curve called with empty legs")
        return []

    if spot <= 0:
        logger.error("compute_payoff_curve: spot=%s is invalid", spot)
        return []

    # ── Price range: ±10% of current spot ────────────────────────────────────
    # For Nifty at 19000: range is 17100 to 20900.
    # This covers a ±10σ move for σ=15% IV at 30 days (~±1.5% 1σ),
    # ensuring the payoff chart shows all meaningful scenarios.
    lower_price = spot * 0.90
    upper_price = spot * 1.10

    # Generate evenly spaced price points
    step = (upper_price - lower_price) / (num_points - 1) if num_points > 1 else 0
    price_range = [lower_price + i * step for i in range(num_points)]

    curve = []

    for underlying_price in price_range:
        total_pnl = 0.0

        for leg in legs:
            try:
                strike      = float(leg["strike"])
                option_type = leg["option_type"]
                side        = leg.get("side", "buy").lower().strip()
                quantity    = int(leg.get("quantity", 1))
                lot_size    = int(leg.get("lot_size", 50))
                entry_price = float(leg.get("entry_price", 0.0))

                if side not in DIRECTION_SIGN:
                    logger.warning("Unknown side '%s', skipping leg", side)
                    continue

                direction = DIRECTION_SIGN[side]

                # ── P&L at expiry for this leg ────────────────────────────
                # intrinsic: what the option is worth at this underlying price
                # entry_price: what we paid (BUY) or received (SELL) to enter
                #
                # P&L = (intrinsic - entry_price) × qty × lot_size × direction
                #
                # For BUY call: direction=+1, so P&L increases as intrinsic rises
                # For SELL call: direction=-1, so P&L = (entry - intrinsic) × ...
                #                i.e. we keep the premium minus any assignment loss
                intrinsic = _intrinsic_value(option_type, strike, underlying_price)
                leg_pnl = (intrinsic - entry_price) * quantity * lot_size * direction
                total_pnl += leg_pnl

            except (KeyError, TypeError, ValueError) as exc:
                logger.error("Error in payoff computation for leg: %s", exc)
                continue

        curve.append({
            "price": round(underlying_price, 2),
            "pnl":   round(total_pnl, 2),
        })

    return curve


def find_breakevens(curve: list[dict]) -> list[float]:
    """
    Find underlying prices at which total strategy P&L crosses zero.

    Method: linear interpolation between adjacent points where P&L sign changes.
    This is more accurate than just finding the nearest zero-crossing price.

    Returns
    -------
    list of float — sorted list of breakeven prices.
    May be empty if the strategy is always profitable or always losing
    within the ±10% price range (e.g. deep OTM naked short).

    Linear interpolation formula:
        breakeven = p1 + (0 - pnl1) × (p2 - p1) / (pnl2 - pnl1)
        where (p1, pnl1) and (p2, pnl2) are the two adjacent points
        bracketing the zero crossing.
    """
    if len(curve) < 2:
        return []

    breakevens = []

    for i in range(len(curve) - 1):
        pnl1 = curve[i]["pnl"]
        pnl2 = curve[i + 1]["pnl"]
        p1   = curve[i]["price"]
        p2   = curve[i + 1]["price"]

        # Check if P&L crosses zero between these two points
        # A sign change occurs when pnl1 and pnl2 have opposite signs
        # (one positive, one negative — or one is exactly zero)
        if pnl1 * pnl2 < 0:
            # Linear interpolation: find the exact price where P&L = 0
            # Derivation: assuming P&L varies linearly between p1 and p2,
            #   pnl(x) = pnl1 + (pnl2 - pnl1) × (x - p1) / (p2 - p1)
            #   Set pnl(x) = 0 and solve for x:
            denom = pnl2 - pnl1
            if abs(denom) < 1e-10:
                continue  # Avoid division by nearly-zero
            breakeven = p1 + (-pnl1) * (p2 - p1) / denom
            breakevens.append(round(breakeven, 2))

        elif pnl1 == 0.0:
            # Exactly zero at this point (rare but possible)
            breakevens.append(round(p1, 2))

    return sorted(breakevens)


def compute_max_profit_loss(curve: list[dict]) -> dict:
    """
    Compute maximum possible profit and loss from the payoff curve.

    ── IMPORTANT DESIGN DECISION: Unlimited risk handling ───────────────────
    A naked short call has theoretically unlimited loss (if Nifty rallies
    infinitely). A long call has unlimited upside. However, our curve only
    covers ±10% of spot, so "unlimited" positions will show as the worst/best
    value in the curve range, which UNDERSTATES the true risk.

    We use ±999,999,999 (not float("inf")) because JSON does not support
    Infinity and this value would break API responses and frontend rendering.

    Strategy type detection:
    - If the worst loss in the curve is at the curve boundary (leftmost or
      rightmost point), the loss is likely UNLIMITED beyond the curve range.
    - If the best profit is at the boundary, it may be unlimited.

    This detection is a heuristic — a proper unlimited-risk detection would
    require examining the strategy structure directly (e.g. uncovered short call).
    The user-facing UI should display "Unlimited" with the appropriate icon.

    Parameters
    ----------
    curve : list of dicts from compute_payoff_curve()

    Returns
    -------
    dict:
        max_profit : float — maximum profit in ₹ (999999999.0 = unlimited)
        max_loss   : float — maximum loss in ₹ (-999999999.0 = unlimited)
    """
    UNLIMITED_PROFIT = 999_999_999.0
    UNLIMITED_LOSS   = -999_999_999.0

    if not curve:
        return {"max_profit": 0.0, "max_loss": 0.0}

    pnls = [point["pnl"] for point in curve]
    best_pnl  = max(pnls)
    worst_pnl = min(pnls)

    # ── Detect "unlimited" scenarios ──────────────────────────────────────────
    # If the extreme P&L occurs at the BOUNDARY of the curve (first or last
    # point), the strategy is likely unbounded beyond our ±10% window.
    # A naked short call, for example, has worst loss at the rightmost price.
    # A long call has best profit at the rightmost price.
    first_pnl = pnls[0]
    last_pnl  = pnls[-1]

    # Unlimited PROFIT: best pnl is at the right boundary AND it's rising
    # (i.e. the curve is still going up at the right edge)
    is_unlimited_profit = (best_pnl == last_pnl) and (len(pnls) > 1) and (last_pnl > pnls[-2])

    # Unlimited LOSS: worst pnl is at the left OR right boundary AND it's worsening
    is_unlimited_loss = (
        (worst_pnl == first_pnl and first_pnl < pnls[1]) or   # left boundary, going down
        (worst_pnl == last_pnl  and last_pnl  < pnls[-2])     # right boundary, going down
    )

    max_profit = UNLIMITED_PROFIT if is_unlimited_profit else round(best_pnl,  2)
    max_loss   = UNLIMITED_LOSS   if is_unlimited_loss   else round(worst_pnl, 2)

    return {"max_profit": max_profit, "max_loss": max_loss}


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    # ── Test 1: Long call ─────────────────────────────────────────────────────
    print("=" * 60)
    print("Test 1: Long call  K=19000, entry=400")
    legs = [{"strike": 19000, "option_type": "call", "side": "buy",
             "quantity": 1, "lot_size": 50, "entry_price": 400}]
    curve = compute_payoff_curve(legs, spot=19000)
    be = find_breakevens(curve)
    ml = compute_max_profit_loss(curve)
    print(f"  Breakevens: {be}")       # Expected: ~19400
    print(f"  Max profit: {ml['max_profit']}")   # Should be unlimited (999999999)
    print(f"  Max loss: {ml['max_loss']}")        # Should be -20000 (400×50)

    # ── Test 2: Short call ────────────────────────────────────────────────────
    print("=" * 60)
    print("Test 2: Naked short call  K=19500, entry=200")
    legs2 = [{"strike": 19500, "option_type": "call", "side": "sell",
              "quantity": 1, "lot_size": 50, "entry_price": 200}]
    curve2 = compute_payoff_curve(legs2, spot=19000)
    ml2 = compute_max_profit_loss(curve2)
    print(f"  Max profit (premium): {ml2['max_profit']}")  # Should be 10000 (200×50)
    print(f"  Max loss (unlimited): {ml2['max_loss']}")    # Should be -999999999

    # ── Test 3: Iron condor ───────────────────────────────────────────────────
    print("=" * 60)
    print("Test 3: Iron condor (short strangle + long wings)")
    ic_legs = [
        {"strike": 18500, "option_type": "put",  "side": "buy",  "quantity": 1, "lot_size": 50, "entry_price": 50},
        {"strike": 19000, "option_type": "put",  "side": "sell", "quantity": 1, "lot_size": 50, "entry_price": 200},
        {"strike": 19500, "option_type": "call", "side": "sell", "quantity": 1, "lot_size": 50, "entry_price": 200},
        {"strike": 20000, "option_type": "call", "side": "buy",  "quantity": 1, "lot_size": 50, "entry_price": 50},
    ]
    curve3 = compute_payoff_curve(ic_legs, spot=19250)
    ml3 = compute_max_profit_loss(curve3)
    be3 = find_breakevens(curve3)
    print(f"  Max profit: {ml3['max_profit']}")   # Should be ~20000 (400 pts net credit × 50)
    print(f"  Max loss: {ml3['max_loss']}")        # Should be finite (capped by wings)
    print(f"  Breakevens: {be3}")