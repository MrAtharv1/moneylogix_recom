"""
tests/test_portfolio_greeks.py — Test suite for portfolio_greeks.py

Covers all required portfolio Greeks test cases.
Run with: pytest tests/test_portfolio_greeks.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from quant.blackscholes import compute as bs_compute
from quant.portfolio_greeks import aggregate, get_portfolio_pnl


# ─── Shared fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def atm_call_greeks():
    return bs_compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")


@pytest.fixture
def atm_put_greeks():
    return bs_compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")


def make_leg(leg_id, side, greeks, quantity=1, lot_size=50):
    """Build a leg dict for aggregate()."""
    return {
        "id":       leg_id,
        "side":     side,
        "quantity": quantity,
        "lot_size": lot_size,
        "greeks":   greeks,
    }


# ─── Test 1: Long straddle net_delta ≈ 0 ────────────────────────────────────

def test_long_straddle_net_delta_approximately_zero(atm_call_greeks, atm_put_greeks):
    """
    Long straddle = long ATM call + long ATM put.
    Call delta ≈ +0.52, Put delta ≈ -0.48 → net ≈ +0.04 (small drift term).

    The portfolio is nearly delta-neutral:
    - Net delta close to zero (within ±10 when scaled by lot_size=50)
    - Any small residual is the drift term (r + σ²/2) × T in d1

    This makes the straddle a pure volatility bet — profits from large moves
    in either direction, not from directional market movement.
    """
    legs = [
        make_leg("call", "buy", atm_call_greeks, quantity=1, lot_size=50),
        make_leg("put",  "buy", atm_put_greeks,  quantity=1, lot_size=50),
    ]
    result = aggregate(legs)
    net_delta = result["net_delta"]

    # Net delta in position units (scaled by lot_size).
    # |net_delta| < 10 is near-zero for a 50 × lot_size position
    assert abs(net_delta) < 20.0, (
        f"Long straddle net_delta should be near zero. Got {net_delta:.4f}. "
        "Call delta ≈ N(d1) ≈ 0.54, put delta ≈ N(d1) - 1 ≈ -0.46; "
        "sum ≈ 0.08, scaled by 50 = ~4 units."
    )


# ─── Test 2: Single long call × 2 lots × 50 lot_size ────────────────────────

def test_single_long_call_portfolio_delta_equals_bs_delta_times_scale(atm_call_greeks):
    """
    Portfolio delta = per-unit delta × quantity × lot_size × direction.
    For 2 lots of Nifty (lot_size=50), buying a call with delta=0.54:
        portfolio_delta = 0.54 × 2 × 50 × (+1) = 54.0 approximately.

    This tells us: for every 1-point move in Nifty, this position's value
    changes by ~₹54 (delta × quantity × lot_size = rupee delta).
    """
    quantity = 2
    lot_size = 50
    legs = [make_leg("c", "buy", atm_call_greeks, quantity=quantity, lot_size=lot_size)]
    result = aggregate(legs)

    bs_delta = atm_call_greeks["delta"]
    expected_portfolio_delta = bs_delta * quantity * lot_size

    assert result["net_delta"] == pytest.approx(expected_portfolio_delta, rel=0.001), (
        f"Portfolio delta should be BS_delta × qty × lot_size = "
        f"{bs_delta:.4f} × {quantity} × {lot_size} = {expected_portfolio_delta:.4f}. "
        f"Got {result['net_delta']:.4f}."
    )


# ─── Test 3: Short call produces negative portfolio delta ────────────────────

def test_short_call_portfolio_net_delta_is_negative(atm_call_greeks):
    """
    SHORT call has negative portfolio delta.
    Call delta = N(d1) > 0, but selling a call means direction = -1:
        portfolio_delta = delta × qty × lot_size × (-1) < 0

    Interpretation: if Nifty rises 1 point, the short call position LOSES
    rupee_delta = delta × lot_size rupees per lot sold.
    """
    legs = [make_leg("sc", "sell", atm_call_greeks, quantity=1, lot_size=50)]
    result = aggregate(legs)

    assert result["net_delta"] < 0, (
        f"Short call net_delta must be negative. Got {result['net_delta']:.4f}. "
        "Short call delta = call_delta × lot_size × (-1 for sell)."
    )


# ─── Test 4: Sum of leg contributions equals portfolio net Greeks ─────────────

def test_leg_contributions_sum_equals_net_greeks(atm_call_greeks, atm_put_greeks):
    """
    Sum of leg_contributions Greeks must equal portfolio net Greeks.
    This validates the aggregation arithmetic is internally consistent.
    Tests delta, gamma, theta, and vega.
    """
    legs = [
        make_leg("c", "buy",  atm_call_greeks, quantity=1, lot_size=50),
        make_leg("p", "sell", atm_put_greeks,  quantity=2, lot_size=50),
    ]
    result = aggregate(legs)
    contribs = result["leg_contributions"]

    # Sum contributions manually
    sum_delta = sum(c["delta"] for c in contribs)
    sum_gamma = sum(c["gamma"] for c in contribs)
    sum_theta = sum(c["theta"] for c in contribs)
    sum_vega  = sum(c["vega"]  for c in contribs)

    assert sum_delta == pytest.approx(result["net_delta"], abs=0.01), (
        f"Sum of leg deltas ({sum_delta:.4f}) != net_delta ({result['net_delta']:.4f})"
    )
    assert sum_gamma == pytest.approx(result["net_gamma"], abs=0.001), (
        f"Sum of leg gammas ({sum_gamma:.6f}) != net_gamma ({result['net_gamma']:.6f})"
    )
    assert sum_theta == pytest.approx(result["net_theta"], abs=0.1), (
        f"Sum of leg thetas ({sum_theta:.2f}) != net_theta ({result['net_theta']:.2f})"
    )
    assert sum_vega == pytest.approx(result["net_vega"], abs=0.1), (
        f"Sum of leg vegas ({sum_vega:.2f}) != net_vega ({result['net_vega']:.2f})"
    )


# ─── Test 5: BUY + SELL same option = net_delta ≈ 0, net_theta ≈ 0 ──────────

def test_buy_and_sell_same_option_nets_to_zero(atm_call_greeks):
    """
    Buying and selling the same option simultaneously is a perfect hedge:
    every Greek nets exactly to zero (buy +greeks, sell -greeks → sum = 0).

    This is the most fundamental test of the sign convention:
    BUY contributes +greeks, SELL contributes -greeks with same magnitude.
    """
    legs = [
        make_leg("buy",  "buy",  atm_call_greeks, quantity=1, lot_size=50),
        make_leg("sell", "sell", atm_call_greeks, quantity=1, lot_size=50),
    ]
    result = aggregate(legs)

    assert abs(result["net_delta"]) < 0.01, (
        f"Offsetting long/short same option: net_delta must be ≈ 0. Got {result['net_delta']:.6f}"
    )
    assert abs(result["net_theta"]) < 0.01, (
        f"Offsetting long/short same option: net_theta must be ≈ 0. Got {result['net_theta']:.6f}"
    )
    assert abs(result["net_gamma"]) < 1e-8, (
        f"Offsetting long/short same option: net_gamma must be ≈ 0. Got {result['net_gamma']:.8f}"
    )
    assert abs(result["net_vega"]) < 0.01, (
        f"Offsetting long/short same option: net_vega must be ≈ 0. Got {result['net_vega']:.4f}"
    )


# ─── Test 6: Iron condor has positive net_theta ──────────────────────────────

def test_iron_condor_has_positive_net_theta():
    """
    Iron condor = sell strangle + buy wings.
    Net theta should be POSITIVE — the strategy earns time decay.
    Short options have negative theta (bad for holders, good for sellers).
    When we SELL options, we receive their negative theta as positive P&L.
    """
    sp_g = bs_compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")
    sc_g = bs_compute(S=19000, K=19500, T_days=30, r=0.065, sigma=0.15, option_type="call")
    lp_g = bs_compute(S=19000, K=18500, T_days=30, r=0.065, sigma=0.15, option_type="put")
    lc_g = bs_compute(S=19000, K=20000, T_days=30, r=0.065, sigma=0.15, option_type="call")

    legs = [
        make_leg("lp", "buy",  lp_g, lot_size=50),
        make_leg("sp", "sell", sp_g, lot_size=50),
        make_leg("sc", "sell", sc_g, lot_size=50),
        make_leg("lc", "buy",  lc_g, lot_size=50),
    ]
    result = aggregate(legs)

    assert result["net_theta"] > 0, (
        f"Iron condor net_theta must be positive (earns time decay). "
        f"Got {result['net_theta']:.2f}. "
        "Short options have negative theta; selling them flips the sign."
    )


# ─── Test 7: Portfolio P&L — buy then price rises ────────────────────────────

def test_portfolio_pnl_long_call_profit_when_price_rises():
    """
    BUY call: profit = (current_price - entry_price) × lots × lot_size
    Entry at 378, current at 450 → P&L = (450 - 378) × 1 × 50 = ₹3,600
    """
    legs = [{"side": "buy", "quantity": 1, "lot_size": 50, "entry_price": 378.0}]
    pnl = get_portfolio_pnl(legs, current_prices=[450.0])

    expected = (450.0 - 378.0) * 1 * 50   # 72 × 50 = 3600
    assert pnl == pytest.approx(expected, rel=0.01), (
        f"Long call P&L should be ₹{expected:,.0f}. Got ₹{pnl:,.0f}."
    )


def test_portfolio_pnl_short_call_profit_when_price_falls():
    """
    SELL call: profit when price FALLS (option decays).
    Entered short at 378, current price 200 (decayed):
    P&L = (200 - 378) × 1 × 50 × (-1 for sell) = +₹8,900
    """
    legs = [{"side": "sell", "quantity": 1, "lot_size": 50, "entry_price": 378.0}]
    pnl = get_portfolio_pnl(legs, current_prices=[200.0])

    expected = (200.0 - 378.0) * 1 * 50 * (-1)   # -178 × 50 × -1 = +8,900
    assert pnl == pytest.approx(expected, rel=0.01), (
        f"Short call P&L when price falls should be ₹{expected:,.0f}. Got ₹{pnl:,.0f}."
    )


# ─── Test 8: Empty legs returns 0 ────────────────────────────────────────────

def test_aggregate_empty_legs_returns_zeros():
    """Empty legs list should return all-zero result, not crash."""
    result = aggregate([])
    assert result["net_delta"] == 0.0
    assert result["net_theta"] == 0.0
    assert result["leg_contributions"] == []


# ─── Test 9: Lot size scaling works correctly ─────────────────────────────────

def test_lot_size_scaling_nifty_vs_banknifty(atm_call_greeks):
    """
    Nifty lot_size=50 vs BankNifty lot_size=15.
    Same delta, same quantity, different lot sizes → different portfolio deltas.
    """
    nifty_leg = make_leg("n", "buy", atm_call_greeks, quantity=1, lot_size=50)
    bnf_leg   = make_leg("b", "buy", atm_call_greeks, quantity=1, lot_size=15)

    result_nifty = aggregate([nifty_leg])
    result_bnf   = aggregate([bnf_leg])

    bs_delta = atm_call_greeks["delta"]

    assert result_nifty["net_delta"] == pytest.approx(bs_delta * 50, rel=0.001)
    assert result_bnf["net_delta"]   == pytest.approx(bs_delta * 15, rel=0.001)

    # Ratio of portfolio deltas should equal ratio of lot sizes
    assert result_nifty["net_delta"] / result_bnf["net_delta"] == pytest.approx(50 / 15, rel=0.001)


# ─── Test 10: Quantity scaling ────────────────────────────────────────────────

def test_quantity_scaling_doubles_all_greeks(atm_call_greeks):
    """
    2 lots of the same option should give exactly double the Greeks of 1 lot.
    All Greeks are linear in quantity.
    """
    leg_1 = [make_leg("c", "buy", atm_call_greeks, quantity=1, lot_size=50)]
    leg_2 = [make_leg("c", "buy", atm_call_greeks, quantity=2, lot_size=50)]

    result_1 = aggregate(leg_1)
    result_2 = aggregate(leg_2)

    assert result_2["net_delta"] == pytest.approx(result_1["net_delta"] * 2, rel=0.001)
    assert result_2["net_theta"] == pytest.approx(result_1["net_theta"] * 2, rel=0.001)
    assert result_2["net_vega"]  == pytest.approx(result_1["net_vega"]  * 2, rel=0.001)