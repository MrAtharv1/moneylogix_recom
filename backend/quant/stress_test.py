"""
stress_test.py — Scenario analysis: mid-life P&L under price and IV shocks.

─────────────────────────────────────────────────────────────────────
WHAT MAKES STRESS TEST DIFFERENT FROM PAYOFF CHART
─────────────────────────────────────────────────────────────────────
The PAYOFF CHART (payoff.py) shows P&L at EXPIRY — when options have
no time value left. It answers: "If I hold to expiry, what do I make?"

The STRESS TEST shows P&L RIGHT NOW under different market scenarios —
using Black-Scholes to reprice options with shocked inputs. It answers:
"If Nifty drops 3% AND IV spikes 15pp TOMORROW, what happens to my
strategy's value?" This is critical for risk management because:

1. Most traders don't hold to expiry — they close positions early.
2. P&L today depends heavily on IV (vega risk), not just spot (delta risk).
3. An iron condor that looks great on the payoff chart can suffer severe
   mid-life losses if IV spikes (think Nifty after a budget announcement).

─────────────────────────────────────────────────────────────────────
HOW THE MATRIX WORKS
─────────────────────────────────────────────────────────────────────
We construct a 5×7 grid of scenarios:

    Columns (7): Price shocks = -5%, -3%, -1%, 0%, +1%, +3%, +5%
    Rows    (5): IV shocks (pp) = -30, -15, 0, +15, +30

For each of the 35 cells:
    1. shocked_spot = spot × (1 + price_shock)
    2. shocked_iv   = max(0.01, current_iv + iv_shock/100)  [floors at 1%]
    3. Reprice each leg using Black-Scholes with shocked inputs
    4. P&L = sum over legs of (new_price - entry_price) × qty × lot_size × direction

The CENTER cell (row=2, col=3: 0% price, 0pp IV) is the "current" scenario.
Its P&L should be ≈ 0 if positions were entered at fair value today.
(Small non-zero values can arise from bid-ask spread or stale entry prices.)

─────────────────────────────────────────────────────────────────────
READING THE MATRIX (for UI colour coding)
─────────────────────────────────────────────────────────────────────
GREEN cells: positive P&L (strategy profits in this scenario)
RED cells:   negative P&L (strategy loses in this scenario)

For an iron condor:
- Center band (small price moves, stable IV) → GREEN (max profit zone)
- Far left/right (large price moves) → RED (hit short strikes)
- Bottom rows (high IV) → RED (vega losses on short options)
- Top rows (low IV) → GREEN (vega gains as short options lose value)

This table immediately shows a trader WHERE their strategy is vulnerable.
"""

import logging
from typing import Union

# Use relative import — this file is inside the quant/ package
from quant.blackscholes import compute as bs_compute

logger = logging.getLogger(__name__)

# ── Scenario grids ────────────────────────────────────────────────────────────
# Price shocks: percentage change in spot (7 columns)
PRICE_SHOCKS = [-0.05, -0.03, -0.01, 0.0, 0.01, 0.03, 0.05]
PRICE_SHOCK_LABELS = ["-5%", "-3%", "-1%", "0%", "+1%", "+3%", "+5%"]

# IV shocks: absolute percentage point change in IV (5 rows)
# "pp" = percentage point (e.g. +15pp means IV goes from 15% to 30%)
IV_SHOCKS_PP = [-30, -15, 0, 15, 30]
IV_SHOCK_LABELS = ["-30pp", "-15pp", "0pp", "+15pp", "+30pp"]

# Index of the "no shock" scenario (center of the grid)
CENTER_PRICE_IDX = 3   # col index for 0% price shock
CENTER_IV_IDX    = 2   # row index for 0pp IV shock

# Minimum allowed IV after negative shocks (IV can't go to zero/negative)
MIN_IV = 0.01  # 1% floor — below this, BS math degrades badly


def run_stress_matrix(
    legs: list[dict],
    spot: float,
    current_iv: float,
    T_days: int,
    r: float = 0.065
) -> dict:
    """
    Run a 5×7 stress test matrix of mid-life P&L scenarios.

    Parameters
    ----------
    legs       : list of leg dicts, each containing:
                    "strike"      : float  — option strike
                    "option_type" : str    — "call" or "put"
                    "side"        : str    — "buy" or "sell"
                    "quantity"    : int    — number of lots
                    "lot_size"    : int    — shares per lot
                    "entry_price" : float  — premium paid/received at trade entry
                    "iv"          : float  — (optional) leg-specific IV override
                                            If not provided, uses current_iv
    spot       : float — current spot price of the underlying
    current_iv : float — current implied volatility (as decimal, e.g. 0.15)
    T_days     : int   — calendar days remaining to expiry
    r          : float — risk-free rate (default: 6.5% India G-Sec)

    Returns
    -------
    dict:
        matrix            : list[list[float]] — 5 rows × 7 cols P&L grid
        price_shocks      : list[str]  — column headers ["-5%", ..., "+5%"]
        iv_shocks         : list[str]  — row headers ["-30pp", ..., "+30pp"]
        max_loss_scenario : float  — worst P&L across all 35 scenarios (₹)
        max_gain_scenario : float  — best P&L across all 35 scenarios (₹)
        current_pnl       : float  — center cell P&L (0% price, 0pp IV)
    """
    if not legs:
        logger.error("run_stress_matrix: no legs provided")
        return _empty_matrix()

    if spot <= 0 or current_iv <= 0 or T_days <= 0:
        logger.error(
            "run_stress_matrix: invalid inputs spot=%s, current_iv=%s, T_days=%s",
            spot, current_iv, T_days
        )
        return _empty_matrix()

    # ── Build the 5×7 matrix ─────────────────────────────────────────────────
    matrix = []

    for iv_shock_pp in IV_SHOCKS_PP:
        row = []

        for price_shock_pct in PRICE_SHOCKS:
            # ── Step 1: Apply spot price shock ────────────────────────────
            # shocked_spot = spot × (1 + price_shock)
            # e.g. Nifty=19000, shock=-5%: shocked_spot = 19000 × 0.95 = 18050
            shocked_spot = spot * (1.0 + price_shock_pct)

            # ── Step 2: Apply IV shock ────────────────────────────────────
            # iv_shock_pp is in percentage points (pp), not decimal
            # +15pp shock: if current_iv=0.15 → shocked_iv = 0.15 + 0.15 = 0.30
            # -30pp shock: if current_iv=0.20 → shocked_iv = 0.20 - 0.30 = -0.10
            #              → clamped to MIN_IV = 0.01
            iv_shock_decimal = iv_shock_pp / 100.0
            shocked_iv = max(MIN_IV, current_iv + iv_shock_decimal)

            # ── Step 3: Compute P&L for this scenario ────────────────────
            scenario_pnl = _compute_scenario_pnl(legs, shocked_spot, shocked_iv, T_days, r)
            row.append(round(scenario_pnl, 2))

        matrix.append(row)

    # ── Extract summary statistics ────────────────────────────────────────────
    all_pnls = [pnl for row in matrix for pnl in row]

    return {
        "matrix":             matrix,
        "price_shocks":       PRICE_SHOCK_LABELS,
        "iv_shocks":          IV_SHOCK_LABELS,
        "max_loss_scenario":  round(min(all_pnls), 2),   # worst cell
        "max_gain_scenario":  round(max(all_pnls), 2),   # best cell
        "current_pnl":        matrix[CENTER_IV_IDX][CENTER_PRICE_IDX],  # center cell
    }


def _compute_scenario_pnl(
    legs: list[dict],
    shocked_spot: float,
    shocked_iv: float,
    T_days: int,
    r: float
) -> float:
    """
    Compute total portfolio P&L for one specific (spot, IV) scenario.

    For each leg:
        new_option_price = BS reprice with (shocked_spot, leg_strike, T_days, shocked_iv)
        leg_pnl = (new_price - entry_price) × quantity × lot_size × direction

    Sum leg_pnl values for the scenario total.

    Parameters
    ----------
    legs         : list of leg dicts (see run_stress_matrix docstring)
    shocked_spot : float — spot price under this scenario
    shocked_iv   : float — implied volatility under this scenario
    T_days       : int   — days to expiry (unchanged across scenarios)
    r            : float — risk-free rate (unchanged)

    Returns
    -------
    float — total strategy P&L in rupees for this scenario
    """
    DIRECTION = {"buy": 1, "sell": -1}
    total_pnl = 0.0

    for leg in legs:
        try:
            strike      = float(leg["strike"])
            option_type = leg["option_type"]
            side        = leg.get("side", "buy").lower().strip()
            quantity    = int(leg.get("quantity", 1))
            lot_size    = int(leg.get("lot_size", 50))
            entry_price = float(leg.get("entry_price", 0.0))

            # Some strategies use per-leg IV (e.g. skewed volatility surface).
            # If the leg has its own IV, apply the same shock to THAT IV.
            # Otherwise, use the portfolio-level current_iv (shocked_iv is already set).
            # Here we always use shocked_iv (portfolio-level shock) for simplicity.
            # Production would apply the shock to each leg's own IV.
            leg_iv = shocked_iv  # Could also do: max(MIN_IV, float(leg.get("iv", shocked_iv)))

            if side not in DIRECTION:
                logger.warning("Unknown side '%s' in stress test leg, skipping", side)
                continue

            # ── Reprice this option with shocked inputs ────────────────────
            # This is the core of the stress test — Black-Scholes repricing
            # under different (spot, IV) combinations.
            repriced = bs_compute(
                S=shocked_spot,
                K=strike,
                T_days=T_days,
                r=r,
                sigma=leg_iv,
                option_type=option_type
            )

            # If BS returned an error (e.g. expired option), use 0 as new price
            if "error" in repriced:
                new_price = 0.0
                logger.debug(
                    "BS error for shocked_spot=%.0f, K=%.0f, T=%d, iv=%.4f",
                    shocked_spot, strike, T_days, leg_iv
                )
            else:
                new_price = repriced["price"]

            direction = DIRECTION[side]

            # ── P&L for this leg in this scenario ─────────────────────────
            # (new_price - entry_price): price change from entry to this scenario
            # × quantity × lot_size: scale up to position size
            # × direction: +1 for long (profit when price rises), -1 for short
            leg_pnl = (new_price - entry_price) * quantity * lot_size * direction
            total_pnl += leg_pnl

        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Error in stress test scenario leg: %s", exc)
            continue

    return total_pnl


def _empty_matrix() -> dict:
    """Return a zeroed-out matrix structure for error cases."""
    zero_row = [0.0] * len(PRICE_SHOCKS)
    return {
        "matrix":             [zero_row[:] for _ in IV_SHOCKS_PP],
        "price_shocks":       PRICE_SHOCK_LABELS,
        "iv_shocks":          IV_SHOCK_LABELS,
        "max_loss_scenario":  0.0,
        "max_gain_scenario":  0.0,
        "current_pnl":        0.0,
    }


def format_matrix_for_display(result: dict) -> str:
    """
    Pretty-print the stress matrix for debugging / logging.

    Parameters
    ----------
    result : dict from run_stress_matrix()

    Returns
    -------
    str — ASCII table of the matrix with headers
    """
    matrix      = result["matrix"]
    price_labels = result["price_shocks"]
    iv_labels    = result["iv_shocks"]

    col_label = "IV/Price"
    header = f"{col_label:>8} | " + " | ".join(f"{p:>10}" for p in price_labels)
    separator = "-" * len(header)
    lines = [header, separator]

    for i, iv_label in enumerate(iv_labels):
        row_str = f"{iv_label:>8} | "
        row_str += " | ".join(f"{matrix[i][j]:>+10,.0f}" for j in range(len(price_labels)))
        lines.append(row_str)

    lines.append(separator)
    lines.append(f"Center cell P&L (no shock): ₹{result['current_pnl']:+,.0f}")
    lines.append(f"Best scenario:  ₹{result['max_gain_scenario']:+,.0f}")
    lines.append(f"Worst scenario: ₹{result['max_loss_scenario']:+,.0f}")

    return "\n".join(lines)


# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    logging.basicConfig(level=logging.WARNING)

    spot = 19000
    current_iv = 0.15
    T_days = 30

    # Iron condor: entry at theoretical BS prices
    from quant.blackscholes import compute as bs
    sp_price = bs(S=spot, K=19000, T_days=T_days, r=0.065, sigma=current_iv, option_type="put")["price"]
    sc_price = bs(S=spot, K=19500, T_days=T_days, r=0.065, sigma=current_iv, option_type="call")["price"]
    lp_price = bs(S=spot, K=18500, T_days=T_days, r=0.065, sigma=current_iv, option_type="put")["price"]
    lc_price = bs(S=spot, K=20000, T_days=T_days, r=0.065, sigma=current_iv, option_type="call")["price"]

    ic_legs = [
        {"strike": 18500, "option_type": "put",  "side": "buy",  "quantity": 1, "lot_size": 50, "entry_price": lp_price},
        {"strike": 19000, "option_type": "put",  "side": "sell", "quantity": 1, "lot_size": 50, "entry_price": sp_price},
        {"strike": 19500, "option_type": "call", "side": "sell", "quantity": 1, "lot_size": 50, "entry_price": sc_price},
        {"strike": 20000, "option_type": "call", "side": "buy",  "quantity": 1, "lot_size": 50, "entry_price": lc_price},
    ]

    result = run_stress_matrix(ic_legs, spot, current_iv, T_days)
    print(format_matrix_for_display(result))
    print(f"\nCenter cell (expect ≈ 0): ₹{result['current_pnl']:+,.0f}")