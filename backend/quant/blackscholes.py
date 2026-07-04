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

"""blackscholes.py — Black-Scholes option pricing and Greeks computation."""
import math
import logging
from scipy.stats import norm

logger = logging.getLogger(__name__)
DEFAULT_R = 0.065

def compute(S: float, K: float, T_days: int, r: float, sigma: float, option_type: str = "call") -> dict:
    opt = option_type.strip().lower()
    if T_days <= 0:
        # Expired: return intrinsic value
        if opt == "call":
            intrinsic = max(0.0, S - K)
        else:
            intrinsic = max(0.0, K - S)
        return {
            "price": round(intrinsic, 2),
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "pop": 1.0 if intrinsic > 0 else 0.0,
            "error": "expired",
        }
    if sigma <= 0 or S <= 0 or K <= 0:
        return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "pop": 0.0, "error": "invalid_inputs"}

    T = T_days / 365.0
    sqrt_T = math.sqrt(T)
    ln_S_K = math.log(S / K)
    d1 = (ln_S_K + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    Nd1 = norm.cdf(d1)
    Nd2 = norm.cdf(d2)
    Nnd1 = norm.cdf(-d1)
    Nnd2 = norm.cdf(-d2)
    nd1 = norm.pdf(d1)

    pv_K = K * math.exp(-r * T)

    if opt == "call":
        price = S * Nd1 - pv_K * Nd2
    elif opt == "put":
        price = pv_K * Nnd2 - S * Nnd1
    else:
        return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "pop": 0.0, "error": "invalid_inputs"}

    if opt == "call":
        delta = Nd1
    else:
        delta = Nd1 - 1.0

    gamma = nd1 / (S * sigma * sqrt_T)
    time_decay = -(S * nd1 * sigma) / (2.0 * sqrt_T)
    if opt == "call":
        theta_annual = time_decay - r * pv_K * Nd2
    else:
        theta_annual = time_decay + r * pv_K * Nnd2
    theta = theta_annual / 365.0

    vega = (S * nd1 * sqrt_T) / 100.0
    pop = Nd2 if opt == "call" else Nnd2

    return {
        "price": round(price, 2),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 2),
        "vega": round(vega, 2),
        "pop": round(pop, 4),
    }