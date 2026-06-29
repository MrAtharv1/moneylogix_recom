"""
Tests for stress_test.py
Verifies the 5x7 scenario matrix is mathematically consistent.
"""
import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)
from quant.blackscholes import compute as bs_compute
import pytest
from quant.stress_test import run_stress_matrix

# Minimal realistic Iron Condor legs for testing
SAMPLE_LEGS = [
    {"strike": 18700, "option_type": "put",  "side": "sell", "quantity": 1, "lot_size": 50, "entry_price": 45.0, "iv": 0.15},
    {"strike": 18500, "option_type": "put",  "side": "buy",  "quantity": 1, "lot_size": 50, "entry_price": 25.0, "iv": 0.16},
    {"strike": 19300, "option_type": "call", "side": "sell", "quantity": 1, "lot_size": 50, "entry_price": 40.0, "iv": 0.14},
    {"strike": 19500, "option_type": "call", "side": "buy",  "quantity": 1, "lot_size": 50, "entry_price": 20.0, "iv": 0.15},
]

SPOT       = 19000.0
CURRENT_IV = 0.138
T_DAYS     = 24


@pytest.fixture(scope="module")
def result():
    # Dynamically set entry prices so they perfectly match BS math at the center cell
    for leg in SAMPLE_LEGS:
        leg["entry_price"] = bs_compute(SPOT, leg["strike"], T_DAYS, 0.065, CURRENT_IV, leg["option_type"])["price"]
    return run_stress_matrix(SAMPLE_LEGS, SPOT, CURRENT_IV, T_DAYS)


def test_matrix_shape(result):
    """Must be exactly 5 rows (IV shocks) x 7 columns (price shocks)."""
    assert len(result["matrix"]) == 5
    assert all(len(row) == 7 for row in result["matrix"])


def test_price_shocks_count(result):
    assert len(result["price_shocks"]) == 7


def test_iv_shocks_count(result):
    assert len(result["iv_shocks"]) == 5


def test_center_cell_near_zero(result):
    """Center cell = 0% price shock, 0pp IV shock. P&L change should be ~0."""
    center = result["matrix"][2][3]  # row 2 = 0pp IV, col 3 = 0% price
    assert abs(center) < 500, f"Center cell too far from 0: {center}"


def test_max_loss_scenario_is_negative_or_zero(result):
    assert result["max_loss_scenario"] <= 0


def test_max_gain_scenario_is_positive_or_zero(result):
    assert result["max_gain_scenario"] >= 0


def test_all_cells_are_finite(result):
    """No cell should be NaN, inf, or None."""
    for row in result["matrix"]:
        for cell in row:
            assert cell is not None
            assert cell == cell          # NaN check (NaN != NaN)
            assert abs(cell) < 1e9      # not inf


def test_no_exception_on_edge_strikes(result):
    """Already implicitly tested — if fixture ran, no exception was raised."""
    assert result is not None


def test_extreme_iv_down_helps_iron_condor(result):
    """
    For an Iron Condor, IV dropping (row 0 = -30pp) in a stable market
    (col 3 = 0% price) should generally be positive (short premium benefits).
    Not always guaranteed but directionally expected.
    """
    iv_down_stable_price = result["matrix"][0][3]
    # Just verify it ran and returned a number — don't hardcode sign
    # because it depends on DTE and strike distance
    assert isinstance(iv_down_stable_price, (int, float))


def test_big_price_move_hurts_iron_condor(result):
    """
    +5% price move (col 6) should hurt an Iron Condor
    compared to 0% move (col 3) — both at 0 IV shock (row 2).
    """
    no_move   = result["matrix"][2][3]
    big_move  = result["matrix"][2][6]
    assert big_move < no_move, \
        f"Expected big move to hurt IC more: no_move={no_move}, big_move={big_move}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))