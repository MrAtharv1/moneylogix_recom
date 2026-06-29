"""
health_monitor.py — Detect meaningful changes in strategy conditions.

Compares current market state to the state when the strategy was entered.
Only reports changes that exceed significance thresholds — avoids noise.

This is what powers the real-time health monitoring WebSocket.

WHY THRESHOLDS AT ALL?
A WebSocket pushing updates every few seconds will see the underlying
wiggle by a few paise and IV jitter by a hundredth of a percent constantly
— that's just market microstructure noise, not a meaningful change in the
trader's situation. If we surfaced every tick as a "change", the health
feed would be unreadable and the trader would tune it out entirely (the
boy-who-cried-wolf problem). Thresholds are the line between "this is
signal, tell the trader" and "this is noise, stay quiet".
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CHANGE_THRESHOLDS — significance thresholds.
#
# A field is only reported as "changed" if it has moved by at least this
# much since entry. Kept as a single module-level constant (not buried
# inside functions) specifically so they're easy to find and tune in one
# place if the feed turns out too noisy or too quiet in practice — change
# the number here, not in five different if-statements scattered through
# the file.
#
#   iv_change_pp:     IV must move by 1.0 PERCENTAGE POINT to matter.
#                      ("pp" = percentage point, e.g. 13.8% -> 14.8%,
#                      NOT a 1% relative change — percentage points are
#                      the right unit for IV because IV is itself already
#                      a percentage; comparing relative % change of a %
#                      value gets confusing fast.)
#
#   price_change_pct: Underlying must move 0.5% (relative) to matter.
#                      Relative is correct here (unlike IV) because the
#                      underlying's absolute price level is arbitrary —
#                      a ₹100 move means very different things for a
#                      ₹18,000 index vs. a ₹500 stock, but 0.5% means the
#                      same thing for both.
#
#   pnl_change_inr:   P&L must move ₹100 (absolute) to matter. Absolute
#                      INR is the right unit here because P&L itself is
#                      already in currency terms — there's no natural
#                      "relative to what" baseline the way there is for
#                      price (you can't take "0.5% of P&L" when P&L
#                      starts at ₹0).
#
#   delta_change:      Portfolio delta must shift by 0.05 (absolute) to
#                      matter. Delta is already a -1..+1-ish normalized
#                      number, so an absolute threshold is natural — no
#                      unit conversion needed.
#
#   dte_warning_days:  Independent of "change" detection — this is a
#                      static floor: warn whenever DTE drops below 7,
#                      regardless of whether DTE changed today (it always
#                      ticks down by ~1, so a delta-based threshold
#                      wouldn't make sense for this field).
# ---------------------------------------------------------------------------
CHANGE_THRESHOLDS = {
    "iv_change_pp": 1.0,          # IV must change by 1 percentage point to matter
    "price_change_pct": 0.5,      # Price must move 0.5% to matter
    "pnl_change_inr": 100,        # P&L must change ₹100 to matter
    "delta_change": 0.05,         # Portfolio delta must shift 0.05 to matter
    "dte_warning_days": 7,        # Warn when less than 7 days to expiry
}


def _format_inr(value: float) -> str:
    """
    Formats a rupee amount with thousands separators using the Indian
    numbering convention's comma placement for amounts under 1 lakh
    (simple 3-digit grouping — e.g. ₹19,000). We deliberately don't
    implement full Indian lakh/crore grouping (₹1,90,000 style) here,
    since strategy P&L and index levels in this product's range rarely
    exceed a few lakh, and standard comma grouping is unambiguous and
    simpler to test; if the product later needs true lakh/crore display
    for larger notional strategies, this is the single function to extend.
    """
    return f"₹{value:,.0f}"


def _build_iv_diff(entry_iv: float, current_iv: float) -> dict | None:
    """
    Step: compare IV at entry vs. now.

    change is expressed in PERCENTAGE POINTS (current - entry), not a
    relative percentage, because IV is itself a percentage — "IV rose
    from 13.8% to 18.0%" is a 4.2 PERCENTAGE POINT move, not a "30%
    increase" framing that would be technically true but far less
    intuitive for a trader scanning the feed.

    Returns None if the move doesn't clear CHANGE_THRESHOLDS["iv_change_pp"].
    """
    change = current_iv - entry_iv
    if abs(change) < CHANGE_THRESHOLDS["iv_change_pp"]:
        return None

    direction = "up" if change > 0 else "down"
    arrow = "↑" if direction == "up" else "↓"
    label = (
        f"IV {arrow}{abs(change):.1f}pp since entry "
        f"(was {entry_iv:.1f}%, now {current_iv:.1f}%)"
    )
    return {
        "from": entry_iv,
        "to": current_iv,
        "change": change,
        "label": label,
        "direction": direction,
    }


def _build_price_diff(entry_spot: float, current_spot: float) -> dict | None:
    """
    Step: compare underlying spot price at entry vs. now.

    pct is a RELATIVE change (not absolute rupees) — see the
    CHANGE_THRESHOLDS docstring above for why relative is the correct
    unit for price specifically.

    Returns None if the move doesn't clear CHANGE_THRESHOLDS["price_change_pct"].
    """
    if entry_spot == 0:
        # Defensive guard: a zero entry price would make pct change
        # undefined (division by zero). This shouldn't happen for any
        # real instrument, but failing loudly with a log beats a
        # ZeroDivisionError taking down the whole diff computation.
        logger.warning("entry_spot is 0; cannot compute price pct change")
        return None

    pct = ((current_spot - entry_spot) / entry_spot) * 100
    if abs(pct) < CHANGE_THRESHOLDS["price_change_pct"]:
        return None

    direction_arrow = "↑" if pct > 0 else "↓"
    label = (
        f"Underlying {direction_arrow}{abs(pct):.1f}% since entry "
        f"(was {_format_inr(entry_spot)}, now {_format_inr(current_spot)})"
    )
    return {
        "from": entry_spot,
        "to": current_spot,
        "pct": pct,
        "label": label,
    }


def _build_pnl_diff(entry_pnl: float, current_pnl: float) -> dict | None:
    """
    Step: compare P&L at entry (always 0, by definition — see
    snapshot.get_entry_state) vs. current unrealized P&L.

    change is an ABSOLUTE rupee amount — see CHANGE_THRESHOLDS docstring
    for why P&L doesn't have a natural "relative to what" baseline the
    way price does.

    Returns None if the move doesn't clear CHANGE_THRESHOLDS["pnl_change_inr"].
    """
    change = current_pnl - entry_pnl
    if abs(change) < CHANGE_THRESHOLDS["pnl_change_inr"]:
        return None

    arrow = "▲" if change > 0 else "▼"
    label = f"P&L {arrow} {_format_inr(abs(change))} since entry"
    return {
        "from": entry_pnl,
        "to": current_pnl,
        "change": change,
        "label": label,
    }


def _build_delta_diff(entry_delta: float, current_delta: float) -> dict | None:
    """
    Step: compare portfolio net delta at entry vs. now.

    change is ABSOLUTE (delta units), since delta is already a small
    normalized number (-1..+1-ish per lot equivalent) where a relative
    "% change" would be meaningless or wildly unstable near zero (e.g.
    going from delta=0.01 to delta=0.02 is a "100% increase" but a
    practically irrelevant move; the absolute threshold avoids that
    distortion).

    Returns None if the move doesn't clear CHANGE_THRESHOLDS["delta_change"].
    """
    change = current_delta - entry_delta
    if abs(change) < CHANGE_THRESHOLDS["delta_change"]:
        return None

    # Signed formatting (+0.02 / +0.15) rather than unsigned, because for
    # delta specifically the SIGN itself is the meaningful signal (it
    # tells you whether the position has become net long or net short
    # the underlying) — a trader scanning this wants to see the sign at
    # a glance, not just the magnitude.
    label = f"Net delta shifted from {entry_delta:+.2f} to {current_delta:+.2f} since entry"
    return {
        "from": entry_delta,
        "to": current_delta,
        "change": change,
        "label": label,
    }


def compute_health_diff(entry_snapshot: dict, current_state: dict) -> dict:
    """
    Both dicts have keys: {iv, spot, pnl, portfolio_delta, days_to_expiry}

    For each field: compute change, compare to threshold, build label if
    significant.

    Each of the four comparison fields (iv/price/pnl/delta) is wrapped in
    its own try/except for the same "degrade, don't die" reason as
    strategy_builder.py — a malformed or missing field in one slice of
    the snapshot (e.g. portfolio_delta missing because an older snapshot
    predates that field being tracked) shouldn't prevent the other three
    diffs, which are independently computable, from being reported.

    Returns HealthDiff-compatible dict:
    {
        "iv":     None or {from, to, change, label, direction: "up"|"down"},
        "price":  None or {from, to, pct, label},
        "pnl":    None or {from, to, change, label},
        "delta":  None or {from, to, change, label},
        "has_changes": bool,   # True if ANY field is non-None
        "dte_warning": bool    # True if DTE < CHANGE_THRESHOLDS["dte_warning_days"]
    }
    """
    diff = {
        "iv": None,
        "price": None,
        "pnl": None,
        "delta": None,
        "has_changes": False,
        "dte_warning": False,
    }

    try:
        diff["iv"] = _build_iv_diff(entry_snapshot["iv"], current_state["iv"])
    except Exception:
        logger.exception("IV diff computation failed")

    try:
        diff["price"] = _build_price_diff(entry_snapshot["spot"], current_state["spot"])
    except Exception:
        logger.exception("Price diff computation failed")

    try:
        diff["pnl"] = _build_pnl_diff(entry_snapshot["pnl"], current_state["pnl"])
    except Exception:
        logger.exception("P&L diff computation failed")

    try:
        diff["delta"] = _build_delta_diff(
            entry_snapshot["portfolio_delta"], current_state["portfolio_delta"]
        )
    except Exception:
        logger.exception("Delta diff computation failed")

    diff["has_changes"] = any(
        diff[field] is not None for field in ("iv", "price", "pnl", "delta")
    )

    try:
        diff["dte_warning"] = current_state["days_to_expiry"] < CHANGE_THRESHOLDS["dte_warning_days"]
    except Exception:
        logger.exception("DTE warning check failed")
        diff["dte_warning"] = False

    return diff


def should_trigger_explanation(diff: dict) -> bool:
    """
    True if diff has meaningful changes worth explaining to the user.
    Simple gate: return diff.get("has_changes", False)

    This prevents unnecessary AI API calls on stable markets — generating
    a natural-language explanation of "what changed and why it matters"
    costs an LLM call, and calling that on every WebSocket tick (even
    when nothing of substance happened) would be pure cost with zero
    user value. Gating on has_changes means we only pay for an
    explanation when there's actually something to explain.

    Uses .get() rather than diff["has_changes"] so a malformed/partial
    diff dict (e.g. from an upstream error) fails safe to "don't bother
    explaining" rather than raising — silence is the safe default for a
    feature whose entire job is to avoid unnecessary noise/cost.
    """
    return diff.get("has_changes", False)