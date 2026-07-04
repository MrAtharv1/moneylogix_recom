"""margin.py — Simplified SPAN margin estimation for NSE options strategies."""
import logging
from quant.payoff import compute_payoff_curve, compute_max_profit_loss

logger = logging.getLogger(__name__)

NAKED_SHORT_MARGIN_RATE = 0.12
MARGIN_DISCLAIMER = (
    "Estimated margin only. Actual SPAN margin may differ. "
    "Always verify with your broker before trading."
)
UNLIMITED_SENTINEL = -999999999

def _classify_strategy(legs: list[dict]) -> str:
    has_long = any(leg.get("side", "").lower() == "buy" for leg in legs)
    has_short = any(leg.get("side", "").lower() == "sell" for leg in legs)
    if has_short and has_long:
        return "defined_risk"
    elif has_short and not has_long:
        return "naked_short"
    else:
        return "long_only"

def estimate_margin(legs: list[dict], spot: float) -> dict:
    if not legs:
        return {
            "estimated_margin": 0.0,
            "basis": "No legs provided.",
            "is_defined_risk": True,
            "disclaimer": MARGIN_DISCLAIMER,
        }
    if spot <= 0:
        return {
            "estimated_margin": 0.0,
            "basis": "Invalid spot price.",
            "is_defined_risk": False,
            "disclaimer": MARGIN_DISCLAIMER,
        }

    strategy_class = _classify_strategy(legs)
    logger.debug("Strategy class: %s", strategy_class)

    # Long only – margin = premium paid
    if strategy_class == "long_only":
        total_premium = 0.0
        for leg in legs:
            try:
                premium = float(leg.get("entry_price", 0.0))
                qty = int(leg.get("quantity", 1))
                lot = int(leg.get("lot_size", 50))  # Dynamically pull from leg
                total_premium += premium * qty * lot
            except Exception:
                continue
        return {
            "estimated_margin": round(total_premium, 2),
            "basis": "Long options only: margin = total premium paid.",
            "is_defined_risk": True,
            "disclaimer": MARGIN_DISCLAIMER,
        }

    # Defined-risk – max loss from payoff curve
    if strategy_class == "defined_risk":
        try:
            curve = compute_payoff_curve(legs, spot, num_points=200)
            
            # Uses the newly updated analytical detection mechanism
            result = compute_max_profit_loss(curve, legs=legs)
            max_loss = result.get("max_loss", 0.0)
            
            if max_loss <= UNLIMITED_SENTINEL:
                logger.warning("Defined-risk shows unlimited loss – reclassifying")
                strategy_class = "naked_short"
            else:
                margin = abs(max_loss)
                return {
                    "estimated_margin": round(margin, 2),
                    "basis": f"Defined-risk: margin = max loss ₹{margin:,.0f}",
                    "is_defined_risk": True,
                    "disclaimer": MARGIN_DISCLAIMER,
                }
        except Exception as e:
            logger.error("Payoff curve for margin failed: %s", e)

    # Naked short
    short_legs = [leg for leg in legs if leg.get("side", "").lower() == "sell"]
    total = 0.0
    parts = []
    for leg in short_legs:
        try:
            qty = int(leg.get("quantity", 1))
            lot = int(leg.get("lot_size", 50))  # Dynamically pull from leg
            notional = spot * qty * lot
            leg_margin = notional * NAKED_SHORT_MARGIN_RATE
            total += leg_margin
            parts.append(f"leg: ₹{leg_margin:,.0f}")
        except Exception:
            continue

    # Portfolio margin offset for straddles/strangles
    if len(short_legs) == 2:
        margins = []
        for leg in short_legs:
            try:
                notional = spot * int(leg.get("quantity", 1)) * int(leg.get("lot_size", 50))
                margins.append(notional * NAKED_SHORT_MARGIN_RATE)
            except Exception:
                continue
                
        if len(margins) == 2:
            bigger = max(margins)
            smaller = min(margins)
            total = bigger + 0.5 * smaller
            basis = f"Naked straddle/strangle: max + 50% smaller = ₹{total:,.0f}"
        else:
            basis = f"Naked short: 12% of notional. Parts: {', '.join(parts)}"
    else:
        basis = f"Naked/undefined short: 12% of notional. {', '.join(parts)}"

    return {
        "estimated_margin": round(total, 2),
        "basis": basis,
        "is_defined_risk": False,
        "disclaimer": MARGIN_DISCLAIMER,
    }