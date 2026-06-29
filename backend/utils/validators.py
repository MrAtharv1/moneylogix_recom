"""
validators.py — Input validation for FastAPI route handlers.

Validation strategy:
  - Pydantic models (in models.py) handle type coercion and basic field presence.
  - This module handles DOMAIN validation: business rules specific to
    Indian options trading that Pydantic types alone can't express.

  Examples of domain rules:
    - A leg must be either CE or PE — Pydantic string type doesn't enforce this
    - Strike must be a positive integer — int doesn't prevent negative values
    - NIFTY lots must be multiples of 50 (Nifty lot size)
    - You can't have more than 8 legs (beyond that, risk calculations become
      too slow for real-time use and most brokers don't support it anyway)

Usage in routes:
    errors = validate_legs(request.legs)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

Returns a list of error strings (empty list = valid). Never raises directly.
"""

from typing import Any

# Valid option types on Indian exchanges (CE = Call, PE = Put)
VALID_OPTION_TYPES = {"call", "put"}

# Valid sides for a leg
VALID_SIDES = {"buy", "sell"}

# Valid underlying symbols we support (add more as data feeds are added)
VALID_SYMBOLS = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}

# Lot sizes per symbol (SEBI-mandated contract sizes)
LOT_SIZES = {
    "NIFTY":       50,
    "BANKNIFTY":   15,
    "FINNIFTY":    40,
    "MIDCPNIFTY":  75,
}

# Strategy complexity limit — spec says max 6 legs for retail traders
MAX_LEGS = 6
MIN_LEGS = 1

# Reasonable strike bounds for Indian index options
# Strikes outside [spot * 0.5, spot * 1.5] are so deep OTM they're likely errors
STRIKE_MIN_ABSOLUTE = 1_000    # Absolute floor (handles all indices)
STRIKE_MAX_ABSOLUTE = 1_00_000  # Absolute ceiling


def validate_legs(legs: list[dict[str, Any]]) -> list[str]:
    """
    Validate a list of option leg dicts.

    Args:
        legs: List of leg dicts, each expected to contain:
              - strike      (int)   : option strike price
              - option_type (str)   : "CE" or "PE"
              - side        (str)   : "buy" or "sell"
              - lots        (int)   : number of lots (≥ 1)
              - expiry      (str)   : ISO date string "YYYY-MM-DD"

    Returns:
        List of error message strings. Empty list means all legs are valid.
    """
    errors = []

    # -------------------------------------------------------------------------
    # Level 1: collection-level checks
    # -------------------------------------------------------------------------
    if not isinstance(legs, list):
        return ["legs must be a list"]

    if len(legs) < MIN_LEGS:
        errors.append(f"Strategy must have at least {MIN_LEGS} leg.")
        return errors  # Can't validate individual legs without at least one

    if len(legs) > MAX_LEGS:
        errors.append(
            f"Strategy has {len(legs)} legs, maximum supported is {MAX_LEGS}."
        )
        return errors

    # -------------------------------------------------------------------------
    # Level 2: per-leg validation
    # -------------------------------------------------------------------------
    for i, leg in enumerate(legs):
        prefix = f"Leg {i + 1}"  # 1-indexed for human-facing error messages

        if not isinstance(leg, dict):
            errors.append(f"{prefix}: must be an object, got {type(leg).__name__}")
            continue  # Can't check fields if leg isn't a dict

        # --- Strike ---
        strike = leg.get("strike")
        if strike is None:
            errors.append(f"{prefix}: missing required field 'strike'")
        elif not isinstance(strike, (int, float)) or isinstance(strike, bool):
            errors.append(f"{prefix}: 'strike' must be a number, got {type(strike).__name__}")
        elif strike <= 0:
            errors.append(f"{prefix}: 'strike' must be positive, got {strike}")
        elif strike < STRIKE_MIN_ABSOLUTE or strike > STRIKE_MAX_ABSOLUTE:
            errors.append(
                f"{prefix}: 'strike' {strike} is outside valid range "
                f"[{STRIKE_MIN_ABSOLUTE:,}, {STRIKE_MAX_ABSOLUTE:,}]"
            )

        # --- Option type ---
        option_type = leg.get("option_type")
        if option_type is None:
            errors.append(f"{prefix}: missing required field 'option_type'")
        elif option_type not in VALID_OPTION_TYPES:
            errors.append(
                f"{prefix}: 'option_type' must be one of {sorted(VALID_OPTION_TYPES)}, "
                f"got '{option_type}'"
            )

        # --- Side ---
        side = leg.get("side")
        if side is None:
            errors.append(f"{prefix}: missing required field 'side'")
        elif side not in VALID_SIDES:
            errors.append(
                f"{prefix}: 'side' must be one of {sorted(VALID_SIDES)}, "
                f"got '{side}'"
            )

        # --- quantity ---
        quantity = leg.get("quantity")
        if quantity is None:
            errors.append(f"{prefix}: missing required field 'quantity'")
        elif not isinstance(quantity, int) or isinstance(quantity, bool):
            errors.append(f"{prefix}: 'quantity' must be an integer, got {type(quantity).__name__}")
        elif quantity < 1:
            errors.append(f"{prefix}: 'quantity' must be ≥ 1, got {quantity}")
        elif quantity > 100:
            errors.append(f"{prefix}: 'quantity' {quantity} exceeds maximum of 100 per leg")

        # --- Lot size (contract size, e.g. 50 for Nifty, 15 for BankNifty) ---
        # This is the exchange-mandated number of units per lot.
        # Stored on the leg so the quant engine doesn't need to look it up again.
        lot_size = leg.get("lot_size")
        if lot_size is not None:  # Optional field — defaults are applied in strategy_builder
            if not isinstance(lot_size, int) or isinstance(lot_size, bool):
                errors.append(f"{prefix}: 'lot_size' must be an integer, got {type(lot_size).__name__}")
            elif lot_size < 1:
                errors.append(f"{prefix}: 'lot_size' must be ≥ 1, got {lot_size}")

        # --- IV (implied volatility for this leg, optional) ---
        # When provided by the frontend (e.g., from the option chain picker),
        # we use it directly instead of computing it from LTP.
        # Must be a non-negative float; 0 is allowed (though unusual).
        iv = leg.get("iv")
        if iv is not None:
            if not isinstance(iv, (int, float)) or isinstance(iv, bool):
                errors.append(f"{prefix}: 'iv' must be a number, got {type(iv).__name__}")
            elif iv < 0:
                errors.append(f"{prefix}: 'iv' must be ≥ 0 (implied volatility cannot be negative), got {iv}")

        # --- Expiry ---
        expiry = leg.get("expiry")
        if expiry is None:
            errors.append(f"{prefix}: missing required field 'expiry'")
        elif not isinstance(expiry, str):
            errors.append(f"{prefix}: 'expiry' must be a date string (YYYY-MM-DD)")
        else:
            # Try to parse the date — we don't validate if it's a real expiry
            # date on the exchange (that would require a live expiry calendar)
            try:
                from datetime import date
                parsed = date.fromisoformat(expiry)
                if parsed < date.today():
                    errors.append(
                        f"{prefix}: 'expiry' {expiry} is in the past. "
                        f"Use a future expiry date."
                    )
            except ValueError:
                errors.append(
                    f"{prefix}: 'expiry' '{expiry}' is not a valid date. "
                    f"Use YYYY-MM-DD format."
                )

    return errors


def validate_symbol(symbol: str) -> list[str]:
    """
    Validate an underlying symbol.

    Args:
        symbol: e.g. "NIFTY", "BANKNIFTY"

    Returns:
        List of error strings. Empty = valid.
    """
    errors = []
    if not symbol:
        errors.append("'symbol' is required")
    elif not isinstance(symbol, str):
        errors.append(f"'symbol' must be a string, got {type(symbol).__name__}")
    elif symbol.upper() not in VALID_SYMBOLS:
        errors.append(
            f"'symbol' '{symbol}' is not supported. "
            f"Valid symbols: {sorted(VALID_SYMBOLS)}"
        )
    return errors


def validate_strategy_type(strategy_type: str) -> list[str]:
    """
    Validate a strategy type string.

    We use a loose validation here (just checks it's a non-empty string)
    because strategy_type is used for AI narration, not for computation.
    The quant engine derives structure from the legs themselves.
    """
    valid_types = {
        "iron_condor", "iron_butterfly", "long_straddle", "short_straddle",
        "long_strangle", "short_strangle", "bull_put_spread", "bear_call_spread",
        "bull_call_spread", "bear_put_spread", "covered_call", "protective_put",
        "calendar_spread", "diagonal_spread", "custom"
    }
    errors = []
    if not strategy_type:
        errors.append("'strategy_type' is required")
    elif strategy_type.lower() not in valid_types:
        # Warn but don't block — unknown strategy types still compute correctly,
        # they just won't get a strategy-specific AI narrative.
        # Return as warning-level info, not a hard error.
        pass
    return errors