"""
blackscholes.py — Black-Scholes option pricing and Greeks computation.

This module is the mathematical foundation of the entire Strategy Builder.
Every price, every Greek, every risk metric in the UI ultimately calls this.

─────────────────────────────────────────────────────────────────────
MODEL ASSUMPTIONS (you will be asked about these in the defence round)
─────────────────────────────────────────────────────────────────────

1. EUROPEAN-STYLE OPTIONS ONLY
   NSE Nifty and BankNifty index options are European — they can only be
   exercised at expiry, not before. Black-Scholes was derived for European
   options. Using it for American options (equity options) would be wrong
   because early exercise premium is not accounted for.

2. CONSTANT IMPLIED VOLATILITY
   BS assumes σ (sigma) is constant over the option's life. In reality,
   IV changes every second. This is the well-known "volatility smile/skew"
   problem. We handle it by accepting the CURRENT market IV as input
   (the user supplies or we fetch it) rather than computing a theoretical σ.

3. NO DIVIDENDS
   Nifty/BankNifty are index options on non-dividend-paying indices for
   modelling purposes. If you were pricing equity options, you'd need the
   Merton (1973) continuous dividend adjustment: replace S with S·e^(-q·T).

4. CONTINUOUS TRADING, NO TRANSACTION COSTS
   Theoretical assumption. In practice, impact costs and lot sizes mean
   you can't perfectly delta-hedge, but this doesn't affect option pricing
   significantly at the retail analytics level.

5. CONSTANT RISK-FREE RATE
   We use India's 10-year G-Sec rate (0.065 = 6.5%) as a proxy.
   This is standard practice in Indian options analytics (Sensibull, etc.).

WHY THESE ASSUMPTIONS ARE ACCEPTABLE HERE:
For a retail construction and monitoring tool (not a market-maker's
pricing system), BS provides the industry-standard Greeks that every
broker and analytics platform uses. Upgrading to Heston or local vol
models would add complexity without meaningful UX benefit at hackathon scope.
"""

import math
import logging
from scipy.stats import norm  # N() — cumulative normal distribution
import numpy as np

logger = logging.getLogger(__name__)

# ─── Risk-free rate default (India 10-year G-Sec, 2024 proxy) ───────────────
DEFAULT_R = 0.065


def compute(
    S: float,            # Underlying spot price, e.g. 19000.0 (Nifty)
    K: float,            # Strike price, e.g. 19200.0
    T_days: int,         # Calendar days to expiry, e.g. 30
    r: float,            # Risk-free rate as decimal, e.g. 0.065 for 6.5%
    sigma: float,        # Implied volatility as decimal, e.g. 0.20 for 20%
    option_type: str = "call"  # "call" or "put"
) -> dict:
    """
    Compute Black-Scholes option price and all first-order Greeks.

    Parameters
    ----------
    S          : Spot price of the underlying index (e.g. Nifty = 19000)
    K          : Strike price of the option
    T_days     : Calendar days remaining to expiry (use calendar days, not trading days)
    r          : Risk-free rate (annualised, as decimal)
    sigma      : Implied volatility (annualised, as decimal)
    option_type: "call" or "put" (case-insensitive)

    Returns
    -------
    dict with keys:
        price  : float — theoretical option premium in index points
        delta  : float — rate of change of price w.r.t. spot (∂V/∂S)
        gamma  : float — rate of change of delta w.r.t. spot (∂²V/∂S²)
        theta  : float — daily time decay in points (negative for long options)
        vega   : float — price change per 1% rise in IV
        pop    : float — risk-neutral probability of expiring in-the-money

    On invalid inputs (T<=0, sigma<=0, S<=0, K<=0):
        Returns all-zero dict with extra key "error": "invalid_inputs"
        NEVER raises an exception to the caller.
    """

    # ── Normalise option type string ─────────────────────────────────────────
    opt = option_type.strip().lower()

    # ── GUARD RAILS — invalid inputs return safe zero dict ───────────────────
    # These guards prevent math domain errors (log of zero, sqrt of negative)
    if T_days <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        logger.warning(
            "blackscholes.compute received invalid inputs: "
            "S=%s, K=%s, T_days=%s, sigma=%s", S, K, T_days, sigma
        )
        return {
            "price": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "pop": 0.0,
            "error": "invalid_inputs",
        }

    # ── WARN on suspicious (but mathematically valid) inputs ─────────────────
    # These won't crash, but might indicate a data entry error.
    if sigma > 2.0:
        logger.warning("sigma=%.2f is unusually high (>200%%). Possible data error.", sigma)
    if T_days > 365:
        logger.warning("T_days=%d is >1 year. Verify expiry date.", T_days)
    if not (0.33 <= S / K <= 3.0):
        logger.warning(
            "S/K ratio=%.2f is extreme (very deep ITM or OTM). Greeks may be unreliable.",
            S / K
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Convert days to years
    # Black-Scholes requires time in YEARS. We use calendar days / 365.
    # Why 365 not 252? Because NSE options decay over weekends too — the
    # theta clock runs continuously, not just on trading days.
    # ─────────────────────────────────────────────────────────────────────────
    T = T_days / 365.0  # e.g. 30 days → 0.08219 years

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Compute d1 and d2
    #
    # d1 = [ ln(S/K) + (r + σ²/2)·T ] / (σ·√T)
    #
    # Intuition for d1:
    #   - ln(S/K): how far in-the-money we are (log moneyness)
    #   - (r + σ²/2)·T: drift term — the expected growth of the underlying
    #     under risk-neutral measure, adjusted by the Itô correction (σ²/2)
    #   - σ·√T: normalisation — scales by volatility × time
    #
    # d2 = d1 - σ·√T
    #   This is the "adjusted" d1, removing the volatility drift term.
    #   N(d2) is the risk-neutral probability of the option expiring ITM.
    # ─────────────────────────────────────────────────────────────────────────
    sqrt_T = math.sqrt(T)                        # √T  (precomputed, used multiple times)
    ln_S_K = math.log(S / K)                    # ln(S/K) — log moneyness
    d1 = (ln_S_K + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Normal distribution values
    # N(x)  = CDF of standard normal at x  (probability that Z < x)
    # N'(x) = PDF of standard normal at x  (the bell curve height at x)
    #
    # N(d1), N(d2): used in price formula
    # N'(d1):       used in gamma, theta, vega (appears in all three)
    # ─────────────────────────────────────────────────────────────────────────
    Nd1 = norm.cdf(d1)       # N(d1) — used in delta (call) and price
    Nd2 = norm.cdf(d2)       # N(d2) — used in call price and put delta
    Nnd1 = norm.cdf(-d1)     # N(-d1) = 1 - N(d1) — used in put price
    Nnd2 = norm.cdf(-d2)     # N(-d2) = 1 - N(d2) — used in put price
    nd1 = norm.pdf(d1)       # N'(d1) — standard normal PDF, appears in gamma/theta/vega

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Discount factor
    # K·e^(-r·T) is the present value of the strike price.
    # We pay/receive the strike at expiry; discounting it back gives today's value.
    # ─────────────────────────────────────────────────────────────────────────
    pv_K = K * math.exp(-r * T)   # K·e^(-rT) — present value of strike

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: OPTION PRICE
    #
    # Call price = S·N(d1) - K·e^(-rT)·N(d2)
    #   S·N(d1)       : "expected" spot price conditional on finishing ITM
    #   K·e^(-rT)·N(d2): PV of strike paid if option finishes ITM
    #   The difference is the expected payoff, discounted to today.
    #
    # Put price = K·e^(-rT)·N(-d2) - S·N(-d1)
    #   Mirror image: profit when S falls below K.
    #   Can also be derived from Put-Call Parity: P = C - S + K·e^(-rT)
    # ─────────────────────────────────────────────────────────────────────────
    if opt == "call":
        price = S * Nd1 - pv_K * Nd2
    elif opt == "put":
        price = pv_K * Nnd2 - S * Nnd1
    else:
        logger.error("Unknown option_type '%s'. Must be 'call' or 'put'.", option_type)
        return {
            "price": 0.0, "delta": 0.0, "gamma": 0.0,
            "theta": 0.0, "vega": 0.0, "pop": 0.0,
            "error": "invalid_inputs",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: DELTA  (∂V/∂S)
    #
    # Delta = how much the option price changes for a ₹1 move in the underlying.
    # Call delta: ranges from 0 (deep OTM) to +1 (deep ITM)
    # Put  delta: ranges from -1 (deep ITM) to 0 (deep OTM)
    #
    # At-the-money options have delta ≈ ±0.50 (slightly above 0.5 for calls
    # due to the drift term r·T).
    #
    # Call delta = N(d1)
    # Put  delta = N(d1) - 1  (equivalently, -N(-d1))
    #
    # Note: call.delta + |put.delta| = N(d1) + (1 - N(d1)) = 1.0 exactly.
    # This is a useful sanity check in the tests.
    # ─────────────────────────────────────────────────────────────────────────
    if opt == "call":
        delta = Nd1
    else:
        delta = Nd1 - 1.0   # This gives a negative number for puts, as expected

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: GAMMA  (∂²V/∂S²  or  ∂delta/∂S)
    #
    # Gamma = rate at which delta changes as spot moves.
    # High gamma means delta changes rapidly → position needs frequent rehedging.
    # ATM options have the highest gamma; deep ITM/OTM have near-zero gamma.
    #
    # Gamma = N'(d1) / (S·σ·√T)
    #
    # Gamma is ALWAYS POSITIVE for both long calls AND long puts.
    # (Short positions have negative gamma — gamma risk.)
    # ─────────────────────────────────────────────────────────────────────────
    gamma = nd1 / (S * sigma * sqrt_T)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: THETA  (∂V/∂T, reported as DAILY decay)
    #
    # Theta = how much option value you lose per calendar day just from
    # the passage of time, all else equal. Almost always negative for long
    # options (time is working against buyers and for sellers).
    #
    # The raw BS theta formula gives change per YEAR. We divide by 365 to
    # get daily theta. (Some books divide by 252; we use 365 for consistency
    # with the calendar-day T convention used above.)
    #
    # Call theta (annual) = -[S·N'(d1)·σ / (2·√T)] - r·K·e^(-rT)·N(d2)
    # Put  theta (annual) = -[S·N'(d1)·σ / (2·√T)] + r·K·e^(-rT)·N(-d2)
    #
    # The first term (always negative) is the "pure" time decay.
    # The second term is the carrying cost of holding the position.
    # For calls it is negative (adds to decay); for puts it is positive
    # (partially offsets decay because puts gain from the interest saved).
    # ─────────────────────────────────────────────────────────────────────────
    time_decay_component = -(S * nd1 * sigma) / (2.0 * sqrt_T)  # always negative

    if opt == "call":
        theta_annual = time_decay_component - r * pv_K * Nd2
    else:
        theta_annual = time_decay_component + r * pv_K * Nnd2

    theta = theta_annual / 365.0   # Convert to per-calendar-day theta

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9: VEGA  (∂V/∂σ, per 1% change in IV)
    #
    # Vega = how much the option price changes if IV rises by 1 percentage point.
    # ALWAYS POSITIVE for long options (more vol → higher option premium always).
    #
    # Raw vega (per unit σ) = S·N'(d1)·√T
    # We divide by 100 to express it as "per 1% IV move" (industry convention).
    #
    # Vega is the same for calls and puts with the same inputs. This follows
    # from put-call parity: C - P = S - K·e^(-rT), so dC/dσ = dP/dσ.
    # ─────────────────────────────────────────────────────────────────────────
    vega = (S * nd1 * sqrt_T) / 100.0   # Points gained per 1pp rise in IV

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10: PROBABILITY OF PROFIT PROXY  (PoP)
    #
    # N(d2) = risk-neutral probability that the underlying finishes ABOVE
    # the strike at expiry. This is the standard practitioner approximation
    # for long call PoP. It's not the real-world probability (which would
    # require the equity risk premium), but it's the standard industry metric.
    #
    # Long call PoP  = N(d2)   → probability of ending ITM (above K)
    # Long put PoP   = N(-d2)  → probability of ending ITM (below K)
    # ─────────────────────────────────────────────────────────────────────────
    pop = Nd2 if opt == "call" else Nnd2

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 11: Round and return
    # Rounding as specified: price→2dp, delta→4dp, gamma→6dp, theta→2dp,
    # vega→2dp, pop→4dp.
    # ─────────────────────────────────────────────────────────────────────────
    return {
        "price": round(price, 2),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 2),   # e.g. -6.23 means you lose 6.23 pts/day
        "vega": round(vega, 2),     # e.g. 52.18 means +52 pts if IV rises 1%
        "pop": round(pop, 4),       # e.g. 0.4982 → ~50% chance of ending ITM
    }


# ─────────────────────────────────────────────────────────────────────────────
# QUICK VERIFICATION (run this file directly to sanity-check output)
# python -m quant.blackscholes
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.WARNING)

    print("─" * 60)
    print("Test 1: ATM Call — S=K=19000, T=30d, σ=15%, r=6.5%")
    r1 = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")
    print(json.dumps(r1, indent=2))
    # Expected: price ≈ 390-420, delta ≈ 0.52

    print("─" * 60)
    print("Test 2: OTM Call — S=19000, K=19500")
    r2 = compute(S=19000, K=19500, T_days=30, r=0.065, sigma=0.15, option_type="call")
    print(json.dumps(r2, indent=2))
    # Expected: delta < 0.35

    print("─" * 60)
    print("Test 3: OTM Put — S=19000, K=18500")
    r3 = compute(S=19000, K=18500, T_days=30, r=0.065, sigma=0.15, option_type="put")
    print(json.dumps(r3, indent=2))
    # Expected: |delta| < 0.35

    print("─" * 60)
    print("Test 4: Invalid input — T_days=0")
    r4 = compute(S=19000, K=19000, T_days=0, r=0.065, sigma=0.15)
    print(json.dumps(r4, indent=2))
    # Expected: all zeros + error key

    print("─" * 60)
    print("Put-Call Parity check: C - P ≈ S - K·e^(-rT)")
    call = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="call")
    put  = compute(S=19000, K=19000, T_days=30, r=0.065, sigma=0.15, option_type="put")
    T = 30 / 365.0
    parity_lhs = call["price"] - put["price"]
    parity_rhs = 19000 - 19000 * math.exp(-0.065 * T)
    print(f"  C - P = {parity_lhs:.2f}")
    print(f"  S - K·e^(-rT) = {parity_rhs:.2f}")
    print(f"  Difference: {abs(parity_lhs - parity_rhs):.4f} (should be < 1.0)")