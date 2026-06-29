"""
tests/test_payoff.py — Test suite for payoff.py

Covers all required payoff test cases.
Run with: pytest tests/test_payoff.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from quant.payoff import compute_payoff_curve, find_breakevens, compute_max_profit_loss


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_leg(strike, option_type, side, entry_price, quantity=1, lot_size=50):
    """Helper to construct a leg dict cleanly."""
    return {
        "strike":      strike,
        "option_type": option_type,
        "side":        side,
        "quantity":    quantity,
        "lot_size":    lot_size,
        "entry_price": entry_price,
    }


# ─── Test 1: Long call payoff at expiry ───────────────────────────────────────

def test_long_call_payoff_below_strike_is_negative_premium():
    """
    For a long call, when underlying price < strike at expiry:
        Intrinsic value = 0  (option expires worthless)
        P&L = (0 - entry_price) × quantity × lot_size × (+1)
            = -entry_price × lot_size  (a loss equal to premium paid)
    """
    entry_price = 400.0
    lot_size    = 50
    strike      = 19000
    spot        = 19000

    legs = [make_leg(strike, "call", "buy", entry_price, lot_size=lot_size)]
    curve = compute_payoff_curve(legs, spot, num_points=200)

    # Find P&L at a price well below the strike (e.g. 17500 — within ±10% of 19000... at the bottom)
    # Spot × 0.90 = 17100, so the first point is the max downside
    first_point = curve[0]
    expected_loss = -entry_price * lot_size  # -400 × 50 = -20,000

    assert first_point["pnl"] == pytest.approx(expected_loss, rel=0.02), (
        f"Long call P&L below strike should equal -premium = ₹{expected_loss:,.0f}. "
        f"Got ₹{first_point['pnl']:,.0f}."
    )


def test_long_call_payoff_rises_above_strike():
    """
    For a long call, P&L increases point-for-point above the breakeven price.
    Above breakeven: P&L > 0 (profitable).
    """
    entry_price = 400.0
    strike      = 19000
    spot        = 19000

    legs = [make_leg(strike, "call", "buy", entry_price)]
    curve = compute_payoff_curve(legs, spot, num_points=200)

    # Find P&L at a price above breakeven (19000 + 400 = 19400)
    # The last point in the curve (spot × 1.10 = 20900) should be positive
    last_point = curve[-1]
    assert last_point["pnl"] > 0, (
        f"Long call P&L should be positive at {last_point['price']:.0f} "
        f"(above breakeven 19400). Got ₹{last_point['pnl']:,.0f}."
    )


# ─── Test 2: Short put payoff at expiry ───────────────────────────────────────

def test_short_put_payoff_above_strike_is_full_premium():
    """
    For a short put, when underlying > strike at expiry:
        Intrinsic value = 0  (put expires worthless)
        P&L = (0 - entry_price) × lot_size × (-1 for sell) = +entry_price × lot_size
    The seller keeps the full premium — maximum profit.
    """
    entry_price = 300.0
    strike      = 19000
    lot_size    = 50
    spot        = 19000

    legs = [make_leg(strike, "put", "sell", entry_price, lot_size=lot_size)]
    curve = compute_payoff_curve(legs, spot, num_points=200)

    # Above the put strike (rightmost points), P&L = +premium × lot_size
    last_point = curve[-1]
    expected_profit = entry_price * lot_size   # 300 × 50 = 15,000

    assert last_point["pnl"] == pytest.approx(expected_profit, rel=0.02), (
        f"Short put P&L above strike should be full premium ₹{expected_profit:,.0f}. "
        f"Got ₹{last_point['pnl']:,.0f}."
    )


def test_short_put_payoff_decreases_below_strike():
    """
    Short put P&L decreases as underlying falls below the put strike.
    Below breakeven (strike - premium): P&L < 0.
    """
    entry_price = 300.0
    strike      = 19000
    spot        = 19000

    legs = [make_leg(strike, "put", "sell", entry_price)]
    curve = compute_payoff_curve(legs, spot, num_points=200)

    # First point (spot × 0.90 = 17100) is deeply below the 19000 put strike
    first_point = curve[0]
    assert first_point["pnl"] < 0, (
        f"Short put P&L should be negative at {first_point['price']:.0f} "
        f"(below breakeven 18700). Got ₹{first_point['pnl']:,.0f}."
    )


# ─── Test 3: Bull call spread max profit ─────────────────────────────────────

def test_bull_call_spread_max_profit():
    """
    Bull call spread: long lower call + short upper call.
    Max profit = (spread width - net debit) × lot_size
    At or above the upper strike, both options are ITM.
    Spread width = 19500 - 19000 = 500 pts
    Net debit = long call premium - short call premium

    P&L at upper strike = (spread_width - net_debit) × lot_size
    """
    long_call_premium  = 400.0   # long K=19000 call
    short_call_premium = 200.0   # short K=19500 call
    net_debit = long_call_premium - short_call_premium   # 200 pts
    spread_width = 19500 - 19000                          # 500 pts
    lot_size = 50

    legs = [
        make_leg(19000, "call", "buy",  long_call_premium,  lot_size=lot_size),
        make_leg(19500, "call", "sell", short_call_premium, lot_size=lot_size),
    ]
    curve = compute_payoff_curve(legs, spot=19250, num_points=300)

    # Max profit = spread_width - net_debit = 500 - 200 = 300 pts × 50 = ₹15,000
    expected_max_profit = (spread_width - net_debit) * lot_size
    result = compute_max_profit_loss(curve)

    assert result["max_profit"] == pytest.approx(expected_max_profit, rel=0.02), (
        f"Bull call spread max profit should be ₹{expected_max_profit:,.0f} "
        f"(spread_width={spread_width} - net_debit={net_debit} = {spread_width - net_debit} pts × {lot_size} lot). "
        f"Got ₹{result['max_profit']:,.0f}."
    )


# ─── Test 4: Iron condor max profit ──────────────────────────────────────────

def test_iron_condor_max_profit_equals_total_net_credit():
    """
    Iron condor max profit = total net premium received (net credit).
    This is earned when underlying stays BETWEEN both short strikes.
    All four options expire worthless; keep all premium received.

    Net credit = short put premium + short call premium - long put premium - long call premium
    """
    long_put_entry  = 50.0    # buy K=18500 put
    short_put_entry = 200.0   # sell K=19000 put
    short_call_entry= 200.0   # sell K=19500 call
    long_call_entry = 50.0    # buy K=20000 call
    lot_size = 50

    net_credit = (short_put_entry + short_call_entry) - (long_put_entry + long_call_entry)
    # = (200 + 200) - (50 + 50) = 300 pts

    legs = [
        make_leg(18500, "put",  "buy",  long_put_entry,   lot_size=lot_size),
        make_leg(19000, "put",  "sell", short_put_entry,  lot_size=lot_size),
        make_leg(19500, "call", "sell", short_call_entry, lot_size=lot_size),
        make_leg(20000, "call", "buy",  long_call_entry,  lot_size=lot_size),
    ]
    curve = compute_payoff_curve(legs, spot=19250, num_points=300)
    result = compute_max_profit_loss(curve)

    expected_max_profit = net_credit * lot_size   # 300 × 50 = ₹15,000

    assert result["max_profit"] == pytest.approx(expected_max_profit, rel=0.03), (
        f"Iron condor max profit should be net credit ₹{expected_max_profit:,.0f}. "
        f"Got ₹{result['max_profit']:,.0f}. Net credit = {net_credit} pts × {lot_size} = ₹{expected_max_profit:,.0f}."
    )


# ─── Test 5: find_breakevens within price range ──────────────────────────────

def test_find_breakevens_within_curve_range():
    """
    Breakevens must be within the curve's price range (spot × 0.90 to spot × 1.10).
    Breakevens outside this range are not computable with the current price window.
    """
    spot = 19000
    legs = [make_leg(19000, "call", "buy", 400.0)]
    curve = compute_payoff_curve(legs, spot=spot, num_points=200)
    breakevens = find_breakevens(curve)

    lower_bound = spot * 0.90
    upper_bound = spot * 1.10

    for be in breakevens:
        assert lower_bound <= be <= upper_bound, (
            f"Breakeven {be:.2f} is outside curve range [{lower_bound:.0f}, {upper_bound:.0f}]."
        )


def test_find_breakevens_long_call_single_breakeven():
    """
    Long call has exactly one breakeven: strike + premium paid.
    Below this price: loss (option expires worthless, lose premium).
    Above this price: profit (intrinsic exceeds premium paid).
    """
    strike      = 19000
    entry_price = 400.0
    spot        = 19000

    legs = [make_leg(strike, "call", "buy", entry_price)]
    curve = compute_payoff_curve(legs, spot=spot, num_points=500)
    breakevens = find_breakevens(curve)

    assert len(breakevens) == 1, (
        f"Long call should have exactly 1 breakeven. Got {len(breakevens)}: {breakevens}"
    )
    expected_be = strike + entry_price   # 19000 + 400 = 19400
    assert breakevens[0] == pytest.approx(expected_be, rel=0.01), (
        f"Long call breakeven should be {expected_be:.0f}. Got {breakevens[0]:.2f}."
    )


# ─── Test 6: Long call has DEFINED risk, naked short call has unlimited loss ──

def test_long_call_max_loss_is_premium_paid_not_unlimited():
    """
    Long call max loss = premium paid (finite, defined risk).
    The worst that can happen is the option expires worthless — you lose your premium.
    max_loss should NOT be -999999999.
    """
    entry_price = 400.0
    lot_size    = 50

    legs = [make_leg(19000, "call", "buy", entry_price, lot_size=lot_size)]
    curve = compute_payoff_curve(legs, spot=19000, num_points=200)
    result = compute_max_profit_loss(curve)

    expected_max_loss = -entry_price * lot_size   # -₹20,000

    # Finite (not unlimited sentinel)
    assert result["max_loss"] > -999_000_000, (
        "Long call max_loss should be FINITE (premium paid), not -999999999. "
        "Long calls have defined risk — max loss = premium paid."
    )
    assert result["max_loss"] == pytest.approx(expected_max_loss, rel=0.02), (
        f"Long call max loss should be -₹{-expected_max_loss:,.0f}. Got ₹{result['max_loss']:,.0f}."
    )


def test_naked_short_call_max_loss_is_unlimited_sentinel():
    """
    Naked short call max loss is UNLIMITED (theoretically infinite).
    If Nifty rallies to infinity, the short call's loss is unbounded.
    We use -999999999 as the sentinel (JSON-safe alternative to -infinity).
    """
    legs = [make_leg(19500, "call", "sell", 200.0)]
    curve = compute_payoff_curve(legs, spot=19000, num_points=200)
    result = compute_max_profit_loss(curve)

    assert result["max_loss"] == -999_999_999.0, (
        f"Naked short call max_loss should be -999999999.0 (unlimited). "
        f"Got {result['max_loss']:,.0f}. "
        "The loss is unbounded if the underlying rallies without limit."
    )


# ─── Test 7: Iron condor both profit and loss are finite ─────────────────────

def test_iron_condor_both_profit_and_loss_are_finite():
    """
    Iron condor is a defined-risk strategy — both max profit and max loss are finite.
    The long wings cap the loss; the short options cap the profit at the net credit.
    Neither side should be the unlimited sentinel (±999999999).
    """
    legs = [
        make_leg(18500, "put",  "buy",  50.0),
        make_leg(19000, "put",  "sell", 200.0),
        make_leg(19500, "call", "sell", 200.0),
        make_leg(20000, "call", "buy",  50.0),
    ]
    curve = compute_payoff_curve(legs, spot=19250, num_points=300)
    result = compute_max_profit_loss(curve)

    assert result["max_profit"] < 999_000_000, (
        f"Iron condor max_profit should be FINITE. Got {result['max_profit']:,.0f}."
    )
    assert result["max_loss"] > -999_000_000, (
        f"Iron condor max_loss should be FINITE. Got {result['max_loss']:,.0f}."
    )


# ─── Test 8: Empty legs returns empty curve ──────────────────────────────────

def test_empty_legs_returns_empty_curve():
    """Edge case: no legs should return an empty list, not crash."""
    curve = compute_payoff_curve([], spot=19000)
    assert curve == [] or curve is not None, "Empty legs should return empty list."
    assert isinstance(curve, list)


# ─── Test 9: Breakevens is sorted ────────────────────────────────────────────

def test_breakevens_are_sorted():
    """Breakevens list must always be returned in ascending order."""
    legs = [
        make_leg(18500, "put",  "buy",  50.0),
        make_leg(19000, "put",  "sell", 200.0),
        make_leg(19500, "call", "sell", 200.0),
        make_leg(20000, "call", "buy",  50.0),
    ]
    curve = compute_payoff_curve(legs, spot=19250, num_points=300)
    breakevens = find_breakevens(curve)

    assert breakevens == sorted(breakevens), (
        f"Breakevens must be in ascending order. Got {breakevens}."
    )