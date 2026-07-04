"""portfolio_greeks.py — Aggregate per-leg Greeks to portfolio level."""
import logging
logger = logging.getLogger(__name__)

DIRECTION_SIGN = {"buy": 1, "sell": -1}

def aggregate(legs: list[dict]) -> dict:
    if not legs:
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
        leg_id = leg.get("id")
        if not leg_id:
            raise ValueError(f"Leg is missing a required 'id' attribute: {leg}")

        side = leg.get("side", "").lower().strip()
        if side not in DIRECTION_SIGN:
            raise ValueError(f"Leg '{leg_id}' has an invalid side: '{side}'. Must be 'buy' or 'sell'.")

        try:
            quantity = int(leg["quantity"])
            lot_size = int(leg.get("lot_size", 65))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Leg '{leg_id}' has invalid quantity or lot_size: {exc}")

        greeks = leg.get("greeks")
        if not greeks or not isinstance(greeks, dict):
            raise ValueError(f"Leg '{leg_id}' is missing computed Greeks dict.")

        direction = DIRECTION_SIGN[side]
        scale = direction * quantity * lot_size

        leg_delta = float(greeks.get("delta", 0.0)) * scale
        leg_gamma = float(greeks.get("gamma", 0.0)) * scale
        leg_theta = float(greeks.get("theta", 0.0)) * scale
        leg_vega = float(greeks.get("vega", 0.0)) * scale

        net_delta += leg_delta
        net_gamma += leg_gamma
        net_theta += leg_theta
        net_vega += leg_vega

        leg_contributions.append({
            "leg_id": leg_id,
            "side": side,
            "delta": round(leg_delta, 4),
            "gamma": round(leg_gamma, 6),
            "theta": round(leg_theta, 2),
            "vega": round(leg_vega, 2),
        })

    return {
        "net_delta": round(net_delta, 4),
        "net_gamma": round(net_gamma, 6),
        "net_theta": round(net_theta, 2),
        "net_vega": round(net_vega, 2),
        "leg_contributions": leg_contributions,
    }

def get_portfolio_pnl(legs: list[dict], current_prices: list[float]) -> float:
    if not legs:
        return 0.0
    if len(legs) != len(current_prices):
        raise ValueError(f"Mismatch: {len(legs)} legs provided, but {len(current_prices)} current prices.")

    total = 0.0
    for i, leg in enumerate(legs):
        side = leg.get("side", "").lower().strip()
        if side not in DIRECTION_SIGN:
            raise ValueError(f"Leg '{leg.get('id', i)}' has invalid side '{side}'.")

        try:
            qty = int(leg["quantity"])
            lot = int(leg.get("lot_size", 65))
            entry = float(leg["entry_price"])
            current = float(current_prices[i])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Leg '{leg.get('id', i)}' is missing or has invalid pricing/size data: {exc}")

        direction = DIRECTION_SIGN[side]
        total += (current - entry) * qty * lot * direction

    return round(total, 2)