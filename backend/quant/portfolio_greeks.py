"""
portfolio_greeks.py — Aggregate per-leg Greeks to portfolio level.

─────────────────────────────────────────────────────────────────────
WHAT THIS MODULE DOES
─────────────────────────────────────────────────────────────────────
A multi-leg options strategy (iron condor, straddle, spread, etc.) is
just a collection of individual option positions. The PORTFOLIO Greeks
are the simple sum of each leg's weighted Greeks.

Why do we sum Greeks? Because Greeks measure linear sensitivities
(to a first-order approximation), and linear sensitivities add up.
If I'm long 1 lot of a call (delta=+0.5) and short 1 lot of a call
(delta=-0.5), my net delta = 0. My portfolio is delta-neutral.

─────────────────────────────────────────────────────────────────────
SIGN CONVENTION — critical to get right
─────────────────────────────────────────────────────────────────────
BUY  (long)  a call/put → you OWN the Greeks → positive contribution
SELL (short) a call/put → you are SHORT the Greeks → negative contribution

Example:
  Short 1 lot of a call with delta=0.5, lot_size=50:
  Contribution = 0.5 × 1 lot × 50 shares × (-1 for sell) = -25.0

Net delta of -25 means: for every 1-point rise in Nifty, you LOSE ₹25.
Net theta of +500 means: every calendar day, you GAIN ₹500 from time decay
(typical for premium sellers in iron condors etc.).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Multiplier applied to a leg's Greeks based on buy/sell direction.
# BUY: you receive positive Greeks exposure (+1)
# SELL: you have negative Greeks exposure (-1)
DIRECTION_SIGN = {"buy": 1, "sell": -1}


def aggregate(legs: list[dict]) -> dict:
    """
    Aggregate individual leg Greeks into portfolio-level net Greeks.

    Parameters
    ----------
    legs : list of dicts, each containing:
        {
            "id"       : str   — unique leg identifier
            "side"     : str   — "buy" or "sell"
            "quantity" : int   — number of lots (e.g. 2 = 2 lots)
            "lot_size" : int   — shares per lot (Nifty=50, BankNifty=15)
            "greeks"   : dict  — output from blackscholes.compute()
                                 keys: delta, gamma, theta, vega, price, pop
        }

    Returns
    -------
    dict:
        net_delta           : float — portfolio delta (₹ per 1-pt move in index)
        net_gamma           : float — portfolio gamma
        net_theta           : float — daily P&L from time decay in index points
        net_vega            : float — portfolio vega (per 1pp IV move)
        leg_contributions   : list  — per-leg breakdown for UI display
    """
    if not legs:
        logger.warning("aggregate() called with empty legs list")
        return {
            "net_delta": 0.0,
            "net_gamma": 0.0,
            "net_theta": 0.0,
            "net_vega": 0.0,
            "leg_contributions": [],
        }

    net_delta = 0.0
    net_gamma = 0.0
    net_theta = 0.0
    net_vega = 0.0
    leg_contributions = []

    for leg in legs:
        try:
            leg_id   = leg.get("id", "unknown")
            side     = leg.get("side", "buy").lower().strip()
            quantity = int(leg.get("quantity", 1))   # number of lots
            lot_size = int(leg.get("lot_size", 50))  # Nifty default
            greeks   = leg.get("greeks", {})

            # ── Validate side ─────────────────────────────────────────────
            if side not in DIRECTION_SIGN:
                logger.error("Leg '%s' has unknown side='%s'. Defaulting to buy.", leg_id, side)
                side = "buy"

            # ── Direction multiplier ──────────────────────────────────────
            # +1 for BUY (you own the exposure)
            # -1 for SELL (you are short the exposure)
            direction = DIRECTION_SIGN[side]

            # ── Scaling factor ────────────────────────────────────────────
            # Greeks from blackscholes.compute() are PER OPTION (1 share).
            # Multiply by lots × lot_size to get POSITION-level Greeks.
            # e.g. 2 lots × 50 shares/lot = exposure for 100 Nifty index units
            scale = direction * quantity * lot_size

            # ── Weighted Greeks for this leg ──────────────────────────────
            leg_delta = greeks.get("delta", 0.0) * scale
            leg_gamma = greeks.get("gamma", 0.0) * scale
            leg_theta = greeks.get("theta", 0.0) * scale
            leg_vega  = greeks.get("vega",  0.0) * scale

            # ── Accumulate into portfolio totals ──────────────────────────
            net_delta += leg_delta
            net_gamma += leg_gamma
            net_theta += leg_theta
            net_vega  += leg_vega

            leg_contributions.append({
                "leg_id"   : leg_id,
                "side"     : side,
                "delta"    : round(leg_delta, 4),
                "gamma"    : round(leg_gamma, 6),
                "theta"    : round(leg_theta, 2),
                "vega"     : round(leg_vega, 2),
            })

        except (TypeError, ValueError, KeyError) as exc:
            # Never crash the caller — log and skip the bad leg
            logger.error("Error processing leg '%s': %s", leg.get("id", "?"), exc)
            continue

    return {
        "net_delta": round(net_delta, 4),
        "net_gamma": round(net_gamma, 6),
        "net_theta": round(net_theta, 2),
        "net_vega" : round(net_vega, 2),
        "leg_contributions": leg_contributions,
    }


def get_portfolio_pnl(legs: list[dict], current_prices: list[float]) -> float:
    """
    Compute current unrealised P&L of the portfolio in rupees (₹).

    P&L per leg = (current_price - entry_price) × quantity × lot_size × direction
    Direction: BUY positions profit when price rises, SELL positions when it falls.

    Parameters
    ----------
    legs          : list of leg dicts, each must have:
                    "side", "quantity", "lot_size", "entry_price"
    current_prices: list of current option prices, aligned with legs list
                    current_prices[i] corresponds to legs[i]

    Returns
    -------
    float — total unrealised P&L in rupees (index points × lot_size × lots)
            Positive = profit, Negative = loss

    Notes
    -----
    - Monetary value: 1 Nifty point = ₹50 (the lot size acts as rupee multiplier)
    - entry_price must already be in index points (the premium paid/received)
    """
    if not legs:
        return 0.0

    if len(legs) != len(current_prices):
        logger.error(
            "get_portfolio_pnl: legs count (%d) != current_prices count (%d)",
            len(legs), len(current_prices)
        )
        return 0.0

    total_pnl = 0.0

    for i, leg in enumerate(legs):
        try:
            side         = leg.get("side", "buy").lower().strip()
            quantity     = int(leg.get("quantity", 1))
            lot_size     = int(leg.get("lot_size", 50))
            entry_price  = float(leg.get("entry_price", 0.0))
            current_price = float(current_prices[i])

            if side not in DIRECTION_SIGN:
                logger.warning("Unknown side '%s' in leg %d, skipping.", side, i)
                continue

            direction = DIRECTION_SIGN[side]

            # ── P&L formula ───────────────────────────────────────────────
            # For a BUY:  profit when current_price > entry_price
            # For a SELL: profit when current_price < entry_price
            #             (direction = -1 flips the sign automatically)
            #
            # Scaling:
            #   quantity × lot_size converts from "per unit" to "per position"
            #   direction handles buy vs sell sign
            #
            # Result is in rupees:
            #   e.g. delta_price=50pts, lot_size=50, qty=1, BUY:
            #        P&L = 50 × 1 × 50 × 1 = ₹2,500 profit
            #
            price_delta = current_price - entry_price
            leg_pnl = price_delta * quantity * lot_size * direction

            total_pnl += leg_pnl

        except (TypeError, ValueError) as exc:
            logger.error("Error computing P&L for leg %d: %s", i, exc)
            continue

    return round(total_pnl, 2)


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    sys.path.insert(0, ".")
    from quant.blackscholes import compute

    logging.basicConfig(level=logging.INFO)

    # Build a long straddle (long call + long put at same strike)
    # Net delta should be approximately 0
    call_greeks = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")
    put_greeks  = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")

    legs = [
        {"id": "long_call", "side": "buy",  "quantity": 1, "lot_size": 50, "greeks": call_greeks},
        {"id": "long_put",  "side": "buy",  "quantity": 1, "lot_size": 50, "greeks": put_greeks},
    ]

    result = aggregate(legs)
    print("Long Straddle portfolio Greeks:")
    print(json.dumps(result, indent=2))
    print(f"Net delta ≈ 0? {abs(result['net_delta']) < 10:.0f} (delta={result['net_delta']:.4f})")
    print(f"Net theta is negative? {result['net_theta'] < 0}")

    # P&L example: bought call at 378, now worth 450 (moved up 10%)
    legs_pnl = [{"side": "buy", "quantity": 1, "lot_size": 50, "entry_price": 378.19}]
    pnl = get_portfolio_pnl(legs_pnl, [450.0])
    print(f"\nP&L on call (entry 378, now 450): ₹{pnl:,.0f} (expect ₹3,590)")