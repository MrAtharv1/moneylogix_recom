"""validators.py — Input validation for FastAPI route handlers."""
from typing import Any
from data.mock_data import asset_config

VALID_OPTION_TYPES = {"call", "put"}
VALID_SIDES = {"buy", "sell"}

# Dynamic symbols from mock_data
VALID_SYMBOLS = set(asset_config.keys()) | {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}

# Hackathon Fallback: The NSE API fails frequently in non-production environments.
# To prevent the validation layer from immediately breaking during the presentation, 
# we hardcode safe index fallbacks. If dynamic fetching succeeds, it will override this,
# but this ensures the pipeline never crashes mid-demo.
FALLBACK_LOT_SIZES = {symbol: config["lot"] for symbol, config in asset_config.items()}
FALLBACK_LOT_SIZES["NIFTY"] = 65
FALLBACK_LOT_SIZES["BANKNIFTY"] = 30
FALLBACK_LOT_SIZES["FINNIFTY"] = 60
FALLBACK_LOT_SIZES["MIDCPNIFTY"] = 120

MAX_LEGS = 6
MIN_LEGS = 1
MAX_QUANTITY_PER_LEG = 50
STRIKE_MIN_ABSOLUTE = 1_000
STRIKE_MAX_ABSOLUTE = 1_00_000

def validate_legs(legs: list[dict[str, Any]]) -> list[str]:
    errors = []
    if not isinstance(legs, list):
        return ["legs must be a list"]
    if len(legs) < MIN_LEGS:
        errors.append(f"Strategy must have at least {MIN_LEGS} leg.")
        return errors
    if len(legs) > MAX_LEGS:
        errors.append(f"Strategy has {len(legs)} legs, maximum {MAX_LEGS}.")
        return errors

    for i, leg in enumerate(legs):
        prefix = f"Leg {i + 1}"
        if not isinstance(leg, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        strike = leg.get("strike")
        if strike is None:
            errors.append(f"{prefix}: missing 'strike'")
        elif not isinstance(strike, (int, float)) or isinstance(strike, bool):
            errors.append(f"{prefix}: 'strike' must be a number")
        elif strike <= 0:
            errors.append(f"{prefix}: 'strike' must be positive")
        elif strike < STRIKE_MIN_ABSOLUTE or strike > STRIKE_MAX_ABSOLUTE:
            errors.append(f"{prefix}: 'strike' outside valid range")

        opt = leg.get("option_type")
        if opt is None:
            errors.append(f"{prefix}: missing 'option_type'")
        elif opt not in VALID_OPTION_TYPES:
            errors.append(f"{prefix}: 'option_type' must be call/put")

        side = leg.get("side")
        if side is None:
            errors.append(f"{prefix}: missing 'side'")
        elif side not in VALID_SIDES:
            errors.append(f"{prefix}: 'side' must be buy/sell")

        qty = leg.get("quantity")
        if qty is None:
            errors.append(f"{prefix}: missing 'quantity'")
        elif not isinstance(qty, int) or isinstance(qty, bool):
            errors.append(f"{prefix}: 'quantity' must be an integer")
        elif qty < 1:
            errors.append(f"{prefix}: 'quantity' must be ≥ 1")
        elif qty > MAX_QUANTITY_PER_LEG:
            errors.append(f"{prefix}: 'quantity' exceeds {MAX_QUANTITY_PER_LEG}")

        lot = leg.get("lot_size")
        if lot is not None:
            if not isinstance(lot, int) or isinstance(lot, bool):
                errors.append(f"{prefix}: 'lot_size' must be an integer")
            elif lot < 1:
                errors.append(f"{prefix}: 'lot_size' must be ≥ 1")

        iv = leg.get("iv")
        if iv is not None:
            if not isinstance(iv, (int, float)) or isinstance(iv, bool):
                errors.append(f"{prefix}: 'iv' must be a number")
            elif iv < 0:
                errors.append(f"{prefix}: 'iv' cannot be negative")

        expiry = leg.get("expiry")
        if expiry is None:
            errors.append(f"{prefix}: missing 'expiry'")
        elif not isinstance(expiry, str):
            errors.append(f"{prefix}: 'expiry' must be a date string")
        else:
            try:
                from datetime import date
                parsed = date.fromisoformat(expiry)
                if parsed < date.today():
                    errors.append(f"{prefix}: 'expiry' {expiry} is in the past")
            except ValueError:
                errors.append(f"{prefix}: 'expiry' invalid format (YYYY-MM-DD)")
    return errors

def validate_symbol(symbol: str) -> list[str]:
    errors = []
    if not symbol:
        errors.append("'symbol' is required")
    elif not isinstance(symbol, str):
        errors.append(f"'symbol' must be a string")
    elif symbol.upper() not in VALID_SYMBOLS:
        errors.append(f"'symbol' '{symbol}' not supported. Valid: {sorted(VALID_SYMBOLS)}")
    return errors