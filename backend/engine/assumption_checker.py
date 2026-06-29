"""
assumption_checker.py — Check if market conditions match strategy assumptions.

Every options strategy has ideal market conditions it was designed for.
An Iron Condor needs a sideways, high-IV market.
A Long Straddle needs a low-IV market expecting a big move.

When conditions change, this checker flags which assumptions have broken.
This is one of the most original features of this platform — no other
retail tool shows this in real time.

WHY HARDCODE THE RULES TABLE INSTEAD OF SOMETHING "SMARTER"?
This table IS the rules engine, intentionally. Every strategy's ideal
conditions are settled options theory — an Iron Condor's edge comes from
selling overpriced premium in a range-bound market, full stop. There's no
hidden pattern for an ML model to discover here; encoding it as data lets
a reviewer read STRATEGY_ASSUMPTIONS top to bottom and verify every claim
against a textbook. That auditability is the point.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# STRATEGY_ASSUMPTIONS — the rules engine.
#
# Each strategy maps to the market regime it was theoretically designed
# to profit from:
#
#   direction:  what underlying movement the strategy wants
#       "sideways"        — wants the underlying to stay in a range
#       "bullish"         — wants the underlying to rise
#       "bearish"         — wants the underlying to fall
#       "big_move"        — wants a large move, direction doesn't matter
#       "neutral_bullish" — fine with flat or mildly up, hurt by a drop
#       "any"             — direction is not a major driver of this trade
#
#   iv_regime:  what implied-volatility environment favors the strategy
#       "high" — strategy is a net premium SELLER, so it benefits from
#                IV being rich now and likely to crush (mean-revert) lower
#       "low"  — strategy is a net premium BUYER, so cheap IV means you're
#                not overpaying for the optionality you're buying
#       "any"  — IV level isn't the primary edge for this structure
#
#   theta: which way time decay cuts for the position
#       "positive"        — net short options: time decay is YOUR profit
#       "negative"         — net long options: time decay erodes YOUR value
#       "slight_negative"  — mixed spread, mostly long-leg-driven decay,
#                             but partially offset by the short leg
#
#   min_dte: minimum days-to-expiry the strategy needs to function as
#             designed. Premium-selling strategies need enough runway for
#             theta to actually do its job; too close to expiry and gamma
#             risk dominates instead.
# ---------------------------------------------------------------------------
STRATEGY_ASSUMPTIONS = {
    "iron_condor": {
        "direction": "sideways",
        "iv_regime": "high",      # benefit from IV crush (premium sellers)
        "theta": "positive",      # time decay works FOR you (short options)
        "min_dte": 15,            # need time for theta to work
    },
    "long_straddle": {
        "direction": "big_move",  # any big move (up or down) is profitable
        "iv_regime": "low",       # buy when IV is cheap
        "theta": "negative",      # time decay works AGAINST you (long options)
        "min_dte": 7,
    },
    "long_strangle": {
        "direction": "big_move",
        "iv_regime": "low",
        "theta": "negative",
        "min_dte": 7,
    },
    "bull_call_spread": {
        "direction": "bullish",
        "iv_regime": "any",       # direction matters more than IV here
        "theta": "slight_negative",
        "min_dte": 7,
    },
    "bull_put_spread": {
        "direction": "bullish",
        "iv_regime": "high",      # sell expensive puts in high IV
        "theta": "positive",
        "min_dte": 7,
    },
    "bear_put_spread": {
        "direction": "bearish",
        "iv_regime": "any",
        "theta": "slight_negative",
        "min_dte": 7,
    },
    "covered_call": {
        "direction": "neutral_bullish",
        "iv_regime": "high",      # sell call when IV is expensive
        "theta": "positive",
        "min_dte": 15,
    },
}

# Mapping used to render a status as both text and an icon in one place,
# so every check function only needs to return the status string and we
# look up the icon once, consistently, rather than each helper inventing
# its own emoji.
_STATUS_ICONS = {
    "valid": "✅",
    "warning": "⚠️",
    "broken": "❌",
}


def _check_direction(expected: str, actual_trend: str, days_to_expiry: int) -> tuple[bool, str]:
    """
    Compares the strategy's required directional regime against the
    market's actual detected trend.

    Returns (is_valid, reason_string). Note this returns a bool, not a
    three-state status — direction is treated as a binary fit/no-fit
    rather than having a "warning" middle state, because a strategy
    either matches the market's directional character or it doesn't;
    there's no useful intermediate ("slightly sideways") for this check
    to express that the theta/liquidity checks meaningfully have.

    `days_to_expiry` is threaded through purely so every reason string —
    including this one — can cite a concrete number, per the platform's
    "no vague reasons" rule (see check_assumptions docstring). It's
    framed as "with N days to expiry" because the directional thesis is
    only meaningful in context of how much time remains for the move to
    play out — a sideways match means less if expiry is 60 days out,
    since plenty of room remains for the trend to change anyway.

    Handles: "sideways", "bullish", "bearish", "big_move",
             "neutral_bullish", "any"
    """
    if expected == "any":
        return True, f"Direction is not a primary driver for this strategy — market trend is '{actual_trend}' with {days_to_expiry} days to expiry"

    if expected == "sideways":
        is_valid = actual_trend == "sideways"
        if is_valid:
            return True, f"Market trend is 'sideways' with {days_to_expiry} days to expiry — matches the range-bound move this strategy is built for"
        return False, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — not sideways, so this strategy needs a range-bound underlying it isn't getting"

    if expected == "big_move":
        # A straddle/strangle profits from movement in EITHER direction,
        # so both "bullish" and "bearish" count as satisfying this
        # condition — only "sideways" (no movement) breaks it. We can't
        # detect an actual realized move purely from a trend label, so
        # this is a proxy: "the market isn't currently flat" is the best
        # signal available from `trend` alone.
        is_valid = actual_trend in ("bullish", "bearish")
        if is_valid:
            return True, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — directional movement supports a big-move strategy"
        return False, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — this strategy needs a strong directional move, not a flat market"

    if expected == "bullish":
        is_valid = actual_trend == "bullish"
        if is_valid:
            return True, f"Market trend is 'bullish' with {days_to_expiry} days to expiry — matches this strategy's directional bias"
        return False, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — not bullish, so this strategy needs the underlying to rise"

    if expected == "bearish":
        is_valid = actual_trend == "bearish"
        if is_valid:
            return True, f"Market trend is 'bearish' with {days_to_expiry} days to expiry — matches this strategy's directional bias"
        return False, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — not bearish, so this strategy needs the underlying to fall"

    if expected == "neutral_bullish":
        # Covered calls profit in flat-to-mildly-up markets and only get
        # hurt by an outright bearish trend (the long stock leg loses
        # value faster than the short call premium can offset).
        is_valid = actual_trend in ("sideways", "bullish")
        if is_valid:
            return True, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — acceptable for a neutral-to-bullish strategy"
        return False, f"Market trend is '{actual_trend}' with {days_to_expiry} days to expiry — this strategy is hurt by a bearish underlying"

    # Unknown expected-direction value: log it and don't silently lie
    # about validity — fail safe by flagging it as broken so a bad config
    # entry in STRATEGY_ASSUMPTIONS doesn't get reported as a quiet "pass".
    logger.warning("Unknown direction assumption '%s' encountered", expected)
    return False, f"Unrecognized direction assumption '{expected}' — unable to verify against trend '{actual_trend}' ({days_to_expiry} days to expiry)"


def _check_iv(expected_regime: str, iv_rank: float) -> tuple[bool, str]:
    """
    Compares the strategy's required IV regime against the current
    IV Rank (0-100, where 100 = highest IV in the last 52 weeks).

    Thresholds:
      "high" → valid if iv_rank >= 60   (rich premium, good for sellers)
      "low"  → valid if iv_rank <= 40   (cheap premium, good for buyers)
      "any"  → always valid

    The 60/40 split (rather than a 50/50 midpoint) intentionally leaves a
    20-point "neutral zone" (41-59) where NEITHER high nor low strategies
    get a clean pass — IV rank in the middle of its range is genuinely
    ambiguous, and a 50/50 split would force a confident high/low verdict
    on data that doesn't actually support one.
    """
    if expected_regime == "any":
        return True, f"IV Rank is {iv_rank:.0f}/100 — IV level isn't a primary driver for this strategy"

    if expected_regime == "high":
        is_valid = iv_rank >= 60
        if is_valid:
            return True, f"IV Rank is {iv_rank:.0f}/100 — high IV is favorable for premium-selling strategies like this one"
        return False, f"IV Rank is {iv_rank:.0f}/100 — too low for a premium-selling strategy, which needs rich (≥60) IV to harvest"

    if expected_regime == "low":
        is_valid = iv_rank <= 40
        if is_valid:
            return True, f"IV Rank is {iv_rank:.0f}/100 — low IV means options are cheap, favorable for a premium-buying strategy"
        return False, f"IV Rank is {iv_rank:.0f}/100 — too high for a premium-buying strategy, which wants cheap (≤40) options"

    logger.warning("Unknown iv_regime assumption '%s' encountered", expected_regime)
    return False, f"Unrecognized IV regime assumption '{expected_regime}' — unable to verify against IV Rank {iv_rank:.0f}/100"


def _check_theta(theta_type: str, days_to_expiry: int, min_dte: int) -> tuple[str, str]:
    """
    Checks whether there's enough runway left for the strategy's theta
    exposure to function as designed.

    Returns a THREE-state status ("valid"|"warning"|"broken") rather than
    a bool, because time decay is genuinely a spectrum, not a cliff:
      - Premium SELLERS (theta="positive") want MORE time, so running low
        on DTE is bad — but it degrades gradually (gamma risk creeps up
        day by day), so we give a "warning" zone before declaring it
        fully broken.
      - Premium BUYERS (theta="negative"/"slight_negative") are hurt by
        time decay itself, so for them min_dte is really a "don't enter
        this trade at all if expiry is basically tomorrow" floor rather
        than an ongoing health metric — but we still apply the same
        warning/broken banding for consistency and because a long option
        bought with very little time left is also fragile in its own way
        (the move has to happen fast).

    Banding (applies regardless of theta_type, using min_dte as the
    reference floor):
      days_to_expiry >= min_dte           → "valid"
      min_dte/2 <= days_to_expiry < min_dte → "warning" (decay zone approaching)
      days_to_expiry < min_dte/2          → "broken" (decay zone/gamma risk dominant)
    """
    if days_to_expiry >= min_dte:
        if theta_type == "positive":
            reason = (
                f"{days_to_expiry} days to expiry — sufficient time for theta decay "
                f"to benefit short positions (needs ≥{min_dte})"
            )
        else:
            reason = (
                f"{days_to_expiry} days to expiry — sufficient time remains before "
                f"theta decay meaningfully erodes long-option value (needs ≥{min_dte})"
            )
        return "valid", reason

    half_floor = min_dte / 2
    if days_to_expiry >= half_floor:
        reason = (
            f"{days_to_expiry} days to expiry — below the ideal {min_dte}-day window; "
            f"gamma risk is rising as expiry approaches"
        )
        return "warning", reason

    reason = (
        f"{days_to_expiry} days to expiry — well below the {min_dte}-day minimum; "
        f"theta/gamma dynamics no longer match this strategy's design"
    )
    return "broken", reason


def _check_liquidity(score: float) -> tuple[str, str]:
    """
    Checks the strategy's aggregate liquidity score (0-100, blending open
    interest, bid/ask spread tightness, and traded volume — see
    strategy_builder.py step 13-14 for how this number is built).

    Banding:
      >= 70        → "valid"   (easy to enter/exit at fair prices)
      40 <= x < 70  → "warning" (tradeable, but expect some slippage)
      < 40          → "broken"  (wide spreads / thin OI — real exit risk)

    This check is strategy-agnostic by design: unlike direction/IV/theta,
    liquidity isn't part of any strategy's "theory" — a thinly-traded
    Iron Condor and a thinly-traded Straddle have exactly the same
    practical problem (you can't get a fair fill), so the same thresholds
    apply to every strategy_type uniformly.
    """
    if score >= 70:
        return "valid", f"Liquidity score is {score:.0f}/100 — tight spreads and healthy open interest, easy to enter or exit"
    if score >= 40:
        return "warning", f"Liquidity score is {score:.0f}/100 — moderate liquidity, expect some slippage on entry/exit"
    return "broken", f"Liquidity score is {score:.0f}/100 — thin open interest or wide spreads, exiting may be costly"


def check_assumptions(strategy_type: str, market_state: dict) -> dict:
    """
    Runs 4 checks: Direction, IV Regime, Time Decay, Liquidity.

    market_state = {
        "iv_rank": float,           # 0-100
        "iv_regime": str,           # "high"|"low"|"neutral" (informational;
                                    #  the numeric iv_rank is what's actually
                                    #  used for the pass/fail check)
        "trend": str,               # "bullish"|"bearish"|"sideways"
        "days_to_expiry": int,
        "liquidity_score": float    # 0-100
    }

    Returns:
    {
        "checks": [
            {"name": str, "status": "valid"|"broken"|"warning", "reason": str, "icon": str}
        ],
        "valid_count": int,
        "total_count": int,
        "score_display": str   # "3/4"
    }
    """
    if strategy_type == "custom":
        # A custom (user-built, not-a-named-strategy) leg combination has
        # no entry in STRATEGY_ASSUMPTIONS — there's no "ideal regime" to
        # check against because the user didn't pick a strategy with a
        # documented thesis. Returning an empty, clearly N/A result is
        # more honest than guessing or defaulting to some other strategy's
        # rules.
        return {"checks": [], "valid_count": 0, "total_count": 0, "score_display": "N/A"}

    assumptions = STRATEGY_ASSUMPTIONS.get(strategy_type)
    if assumptions is None:
        logger.warning("Unknown strategy_type '%s' passed to check_assumptions", strategy_type)
        return {"checks": [], "valid_count": 0, "total_count": 0, "score_display": "N/A"}

    checks = []

    # --- Check 1: Market Direction ---
    try:
        is_valid, reason = _check_direction(
            assumptions["direction"], market_state["trend"], market_state["days_to_expiry"]
        )
        status = "valid" if is_valid else "broken"
        checks.append({
            "name": "Market Direction",
            "status": status,
            "reason": reason,
            "icon": _STATUS_ICONS[status],
        })
    except Exception:
        logger.exception("Direction check failed for strategy_type=%s", strategy_type)
        checks.append({
            "name": "Market Direction", "status": "warning",
            "reason": "Unable to evaluate market direction due to an internal error",
            "icon": _STATUS_ICONS["warning"],
        })

    # --- Check 2: IV Regime ---
    try:
        is_valid, reason = _check_iv(assumptions["iv_regime"], market_state["iv_rank"])
        status = "valid" if is_valid else "broken"
        checks.append({
            "name": "IV Regime",
            "status": status,
            "reason": reason,
            "icon": _STATUS_ICONS[status],
        })
    except Exception:
        logger.exception("IV check failed for strategy_type=%s", strategy_type)
        checks.append({
            "name": "IV Regime", "status": "warning",
            "reason": "Unable to evaluate IV regime due to an internal error",
            "icon": _STATUS_ICONS["warning"],
        })

    # --- Check 3: Time Decay ---
    try:
        status, reason = _check_theta(
            assumptions["theta"], market_state["days_to_expiry"], assumptions["min_dte"]
        )
        checks.append({
            "name": "Time Decay",
            "status": status,
            "reason": reason,
            "icon": _STATUS_ICONS[status],
        })
    except Exception:
        logger.exception("Theta check failed for strategy_type=%s", strategy_type)
        checks.append({
            "name": "Time Decay", "status": "warning",
            "reason": "Unable to evaluate time decay due to an internal error",
            "icon": _STATUS_ICONS["warning"],
        })

    # --- Check 4: Liquidity ---
    try:
        status, reason = _check_liquidity(market_state["liquidity_score"])
        checks.append({
            "name": "Liquidity",
            "status": status,
            "reason": reason,
            "icon": _STATUS_ICONS[status],
        })
    except Exception:
        logger.exception("Liquidity check failed for strategy_type=%s", strategy_type)
        checks.append({
            "name": "Liquidity", "status": "warning",
            "reason": "Unable to evaluate liquidity due to an internal error",
            "icon": _STATUS_ICONS["warning"],
        })

    valid_count = sum(1 for c in checks if c["status"] == "valid")
    total_count = len(checks)

    return {
        "checks": checks,
        "valid_count": valid_count,
        "total_count": total_count,
        "score_display": f"{valid_count}/{total_count}",
    }