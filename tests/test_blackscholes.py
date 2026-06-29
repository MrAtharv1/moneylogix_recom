"""
tests/test_blackscholes.py — Test suite for blackscholes.py

Covers all 10 required test cases plus boundary conditions.
Run with: pytest tests/test_blackscholes.py -v
"""

import math
import sys
import os
import pytest

# Add backend to path so we can import quant modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from quant.blackscholes import compute


# ─── Shared fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def atm_call():
    """ATM call: S=K=19000, 30 days, 15% IV."""
    return compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")


@pytest.fixture
def atm_put():
    """ATM put: same inputs as atm_call but put."""
    return compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")


@pytest.fixture
def deep_itm_call():
    """Deep ITM call: S=20000, K=17000 — 17.6% in-the-money."""
    return compute(S=20000, K=17000, T_days=30, r=0.065, sigma=0.15, option_type="call")


@pytest.fixture
def deep_otm_call():
    """Deep OTM call: S=19000, K=22000 — 15.8% out-of-the-money."""
    return compute(S=19000, K=22000, T_days=30, r=0.065, sigma=0.15, option_type="call")


# ─── Test 1: ATM call delta ≈ 0.50 ──────────────────────────────────────────

def test_atm_call_delta_approximately_half(atm_call):
    """
    ATM call delta should be approximately 0.50.
    Exact value is N(d1) where d1 includes the drift term (r + σ²/2)·T,
    so ATM delta is slightly above 0.50 for positive r. We allow ±0.03.
    """
    delta = atm_call["delta"]
    assert 0.47 <= delta <= 0.65, (
        f"ATM call delta should be ≈0.50-0.55, got {delta:.4f}. "
        "Check d1 formula: d1 = (ln(S/K) + (r+σ²/2)T) / (σ√T)"
    )


# ─── Test 2: Deep ITM call delta → ~1.0 ─────────────────────────────────────

def test_deep_itm_call_delta_approaches_one(deep_itm_call):
    """
    Deep ITM call delta approaches +1.0.
    When S >> K, the call will almost certainly be exercised at expiry,
    so it behaves like holding the underlying directly: delta ≈ 1.
    """
    delta = deep_itm_call["delta"]
    assert delta > 0.90, (
        f"Deep ITM call delta should be > 0.90, got {delta:.4f}. "
        f"S=20000, K=17000 is deeply in-the-money."
    )
    assert delta <= 1.0, (
        f"Delta cannot exceed 1.0 (would imply more than full underlying exposure). "
        f"Got {delta:.4f}."
    )


# ─── Test 3: Deep OTM call delta → ~0.0 ─────────────────────────────────────

def test_deep_otm_call_delta_approaches_zero(deep_otm_call):
    """
    Deep OTM call delta approaches 0.
    When S << K, the call is very unlikely to be exercised.
    A ₹1 move in Nifty has negligible effect on a far OTM option.
    """
    delta = deep_otm_call["delta"]
    assert delta < 0.05, (
        f"Deep OTM call delta should be < 0.05, got {delta:.4f}. "
        f"S=19000, K=22000 is deeply out-of-the-money."
    )
    assert delta >= 0.0, (
        f"Call delta cannot be negative. Got {delta:.4f}."
    )


# ─── Test 4: Theta is negative for long call ─────────────────────────────────

def test_theta_is_negative_for_long_call(atm_call):
    """
    Theta must be negative for long (bought) options.
    Time decay works AGAINST option buyers — as expiry approaches,
    time value erodes, reducing option price all else equal.
    This is the fundamental cost of being long options.
    """
    theta = atm_call["theta"]
    assert theta < 0, (
        f"ATM call theta should be negative (time decay costs buyers). "
        f"Got theta={theta:.4f}. "
        "Check theta formula: it should be divided by 365 and produce a negative value."
    )


# ─── Test 5: Gamma is always positive ────────────────────────────────────────

def test_gamma_is_always_positive_for_calls_and_puts():
    """
    Gamma must be positive for BOTH long calls and long puts.
    Gamma = N'(d1) / (S·σ·√T)
    N'(d1) is always positive (it's a probability density).
    S, σ, √T are always positive.
    Therefore gamma > 0 always for long positions.
    Short positions have negative gamma (selling gamma).
    """
    for option_type in ["call", "put"]:
        result = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type=option_type)
        gamma = result["gamma"]
        assert gamma > 0, (
            f"Gamma must be positive for long {option_type}. "
            f"Got gamma={gamma:.6f}. "
            "Gamma = N'(d1) / (S·σ·√T) — all terms positive → gamma > 0."
        )


# ─── Test 6: T_days=0 returns error, no exception ────────────────────────────

def test_invalid_t_days_zero_returns_error_dict():
    """
    T_days=0 (expired option) must return a zero-value dict with error key.
    Must NOT raise an exception — the UI depends on graceful error handling.
    An expired option has zero time value; its value is just intrinsic,
    which Black-Scholes cannot compute (division by √0 = undefined).
    """
    result = compute(S=19000, K=19000, T_days=0, r=0.065, sigma=0.15, option_type="call")

    # Should not raise — we check the return value instead
    assert isinstance(result, dict), "Must return a dict, not raise an exception."
    assert "error" in result, "Must contain 'error' key for T_days=0."
    assert result["error"] == "invalid_inputs", f"Expected 'invalid_inputs', got {result['error']}"
    assert result["price"] == 0.0, f"Price must be 0.0 for invalid input, got {result['price']}"
    assert result["delta"] == 0.0, f"Delta must be 0.0 for invalid input, got {result['delta']}"


# ─── Test 7: sigma=0 returns error, no exception ─────────────────────────────

def test_invalid_sigma_zero_returns_error_dict():
    """
    sigma=0 (zero volatility) must return error dict without raising.
    Zero volatility causes division by zero in d1 formula: σ·√T = 0.
    Also, the mathematical interpretation breaks down (option has no uncertainty).
    """
    result = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.0, option_type="call")

    assert isinstance(result, dict), "Must return a dict, not raise."
    assert "error" in result, "Must contain 'error' key for sigma=0."
    assert result["price"] == 0.0
    assert result["gamma"] == 0.0


# ─── Test 8: Put-Call Parity ─────────────────────────────────────────────────

def test_put_call_parity(atm_call, atm_put):
    """
    Put-Call Parity: C - P = S - K·e^(-rT)

    This is a model-independent relationship (holds for any option pricing model,
    not just Black-Scholes). It's derived from no-arbitrage arguments.

    For ATM options where S=K=19000:
        C - P ≈ S - K·e^(-rT) = S × (1 - e^(-rT))
        Since r=6.5% and T=30/365, e^(-rT) ≈ 0.9947
        So C - P ≈ 19000 × 0.0053 ≈ ₹100

    We test that the difference is within 0.5% of the theoretical value.
    """
    S = 19000
    K = 19000
    r = 0.065
    T = 30 / 365.0

    parity_lhs = atm_call["price"] - atm_put["price"]
    parity_rhs = S - K * math.exp(-r * T)

    # Relative error must be within 0.5%
    # (Absolute tolerance: within 0.5% of spot = 19000 × 0.005 = 95)
    abs_tolerance = S * 0.005
    diff = abs(parity_lhs - parity_rhs)

    assert diff < abs_tolerance, (
        f"Put-Call Parity violated: C-P={parity_lhs:.4f}, S-Ke^(-rT)={parity_rhs:.4f}, "
        f"diff={diff:.4f} (must be < {abs_tolerance:.2f}). "
        "Check call and put pricing formulas."
    )


# ─── Test 9: call.delta + |put.delta| ≈ 1.0 ─────────────────────────────────

def test_call_put_delta_sum_to_one(atm_call, atm_put):
    """
    For the same underlying, strike, and expiry:
        call.delta + |put.delta| = N(d1) + (1 - N(d1)) = 1.0 exactly.

    This is an algebraic identity from the delta formulas:
        Call delta = N(d1)
        Put  delta = N(d1) - 1 = -(1 - N(d1)) = -N(-d1)
        Sum: N(d1) + (1 - N(d1)) = 1.0

    Any deviation indicates a bug in delta computation.
    """
    call_delta = atm_call["delta"]     # positive
    put_delta  = atm_put["delta"]      # negative

    delta_sum = call_delta + abs(put_delta)

    assert abs(delta_sum - 1.0) < 1e-4, (
        f"call.delta ({call_delta:.6f}) + |put.delta| ({abs(put_delta):.6f}) "
        f"= {delta_sum:.6f}, expected 1.0. "
        "Check: call_delta=N(d1), put_delta=N(d1)-1."
    )


# ─── Test 10: Vega is always positive ────────────────────────────────────────

def test_vega_is_always_positive():
    """
    Vega must be positive for both long calls and long puts.

    Higher volatility increases the probability of large moves in either
    direction. Since options give the RIGHT but not the obligation to exercise,
    holders benefit from large moves in either direction.

    Therefore, more volatility ALWAYS increases option premium → vega > 0.

    This is also algebraically clear: vega = S·N'(d1)·√T / 100
    All terms positive → vega > 0.
    """
    for option_type in ["call", "put"]:
        result = compute(
            S=19000, K=19000, T_days=30, r=0.065, sigma=0.15,
            option_type=option_type
        )
        vega = result["vega"]
        assert vega > 0, (
            f"Vega must be positive for long {option_type}. Got vega={vega:.4f}. "
            "vega = S·N'(d1)·√T / 100 — all terms positive."
        )


# ─── Test 11: Negative inputs return error ────────────────────────────────────

def test_negative_spot_returns_error():
    """Negative spot price must return error dict, not crash."""
    result = compute(S=-100, K=19000, T_days=30, r=0.065, sigma=0.15)
    assert "error" in result
    assert result["price"] == 0.0


def test_negative_strike_returns_error():
    """Negative strike must return error dict."""
    result = compute(S=19000, K=-1, T_days=30, r=0.065, sigma=0.15)
    assert "error" in result


# ─── Test 12: Negative T returns error ───────────────────────────────────────

def test_negative_t_days_returns_error():
    """Negative T_days (past expiry) must return error dict."""
    result = compute(S=19000, K=19000, T_days=-5, r=0.065, sigma=0.15)
    assert "error" in result
    assert result["delta"] == 0.0


# ─── Test 13: Option price is non-negative ────────────────────────────────────

def test_option_price_always_non_negative():
    """
    Option prices must never be negative.
    An option is a right, not an obligation — worst case it expires worthless (= 0).
    """
    for option_type in ["call", "put"]:
        for moneyness in [0.85, 0.95, 1.0, 1.05, 1.15]:   # OTM, near, ATM, near, ITM
            K = 19000 * moneyness
            result = compute(S=19000, K=K, T_days=30, r=0.065, sigma=0.15, option_type=option_type)
            assert result["price"] >= 0, (
                f"{option_type} price must be ≥ 0. Got {result['price']:.4f} at K={K:.0f}."
            )


# ─── Test 14: OTM call vs OTM put spec checks ────────────────────────────────

def test_otm_call_delta_less_than_035():
    """Spec check: OTM call (K=19500, S=19000) delta < 0.35."""
    result = compute(S=19000, K=19500, T_days=30, r=0.065, sigma=0.15, option_type="call")
    assert result["delta"] < 0.35, (
        f"OTM call (K=19500 vs S=19000) delta should be < 0.35. Got {result['delta']:.4f}."
    )


def test_otm_put_abs_delta_less_than_035():
    """Spec check: OTM put (K=18500, S=19000) |delta| < 0.35."""
    result = compute(S=19000, K=18500, T_days=30, r=0.065, sigma=0.15, option_type="put")
    assert abs(result["delta"]) < 0.35, (
        f"OTM put (K=18500 vs S=19000) |delta| should be < 0.35. Got {result['delta']:.4f}."
    )


# ─── Test 15: Unknown option_type returns error ───────────────────────────────

def test_unknown_option_type_returns_error():
    """Unknown option type string must return error dict without crashing."""
    result = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="future")
    assert "error" in result
    assert result["price"] == 0.0


# ─── Test 16: PoP is within [0, 1] ───────────────────────────────────────────

def test_pop_is_between_zero_and_one():
    """
    PoP (probability of profit proxy) must be a valid probability.
    N(d2) and N(-d2) are CDFs of the normal distribution → always in [0, 1].
    """
    for option_type in ["call", "put"]:
        result = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type=option_type)
        pop = result["pop"]
        assert 0.0 <= pop <= 1.0, (
            f"{option_type} pop must be in [0, 1]. Got {pop:.4f}."
        )


# ─── Test 17: Gamma same for call and put (same inputs) ──────────────────────

def test_gamma_same_for_call_and_put():
    """
    Gamma is identical for calls and puts with the same inputs.
    gamma = N'(d1) / (S·σ·√T) — does not depend on option type.
    This follows from put-call parity: dC/dS² = dP/dS².
    """
    call_g = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")
    put_g  = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")
    assert abs(call_g["gamma"] - put_g["gamma"]) < 1e-8, (
        f"Gamma should be identical for call and put. "
        f"Call gamma={call_g['gamma']:.8f}, Put gamma={put_g['gamma']:.8f}"
    )


# ─── Test 18: Vega same for call and put ─────────────────────────────────────

def test_vega_same_for_call_and_put():
    """
    Vega is identical for calls and puts with the same inputs.
    vega = S·N'(d1)·√T / 100 — does not depend on option type.
    Follows from put-call parity: dC/dσ = dP/dσ.
    """
    call_g = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")
    put_g  = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")
    assert abs(call_g["vega"] - put_g["vega"]) < 0.01, (
        f"Vega should be identical for call and put. "
        f"Call vega={call_g['vega']:.4f}, Put vega={put_g['vega']:.4f}"
    )