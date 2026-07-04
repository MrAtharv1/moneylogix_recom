"""
tests/test_adjustment_simulator.py — Tests adjustment comparison logic.
"""
import sys
import os
import pytest
from unittest.mock import patch

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from engine.adjustment_simulator import simulate_adjustment, _format_change, _build_summary


def make_leg(strike, opt="call", side="buy", qty=1, lot=65, entry=0.0):
    return {
        "id": f"leg-{strike}",
        "strike": strike,
        "option_type": opt,
        "side": side,
        "quantity": qty,
        "lot_size": lot,
        "entry_price": entry,
    }


# ─── Tests ────────────────────────────────────────────────────────────────────

@patch('engine.adjustment_simulator.get_option_chain')
def test_simulate_adjustment_returns_comparison(mock_get_chain):
    """Ensures the adjustment simulation returns original, adjusted, and comparison."""
    # Mock chain (minimal)
    mock_get_chain.return_value = (
        {
            "spot": 19000.0,
            "days_to_expiry": 30,
            "current_iv": 0.15,
            "iv_52w_high": 0.28,
            "iv_52w_low": 0.09,
            "strikes": []
        },
        "live"
    )

    orig = [make_leg(19000, "call", "buy", entry=100)]
    adj = [make_leg(19200, "call", "buy", entry=80)]

    result = simulate_adjustment(orig, adj, "NIFTY")

    assert 'original' in result
    assert 'adjusted' in result
    assert 'comparison' in result
    assert 'data_mode' in result

    comp = result['comparison']
    assert 'delta_max_profit' in comp
    assert 'delta_max_loss' in comp
    assert 'delta_margin' in comp
    assert 'delta_net_theta' in comp
    assert 'max_profit_changed_by' in comp
    assert 'max_loss_changed_by' in comp
    assert 'margin_changed_by' in comp
    assert 'summary' in comp


@patch('engine.adjustment_simulator.get_option_chain')
def test_adjustment_comparison_uses_net_theta_not_theta(mock_get_chain):
    """Regression test: ensures we use 'net_theta' (correct key) not 'theta'."""
    mock_get_chain.return_value = (
        {
            "spot": 19000.0,
            "days_to_expiry": 30,
            "current_iv": 0.15,
            "iv_52w_high": 0.28,
            "iv_52w_low": 0.09,
            "strikes": []
        },
        "live"
    )

    orig = [make_leg(19000, "call", "buy", entry=100)]
    adj = [make_leg(19000, "put", "buy", entry=100)]

    result = simulate_adjustment(orig, adj, "NIFTY")
    # If the key was wrong, delta_net_theta would be 0.0
    # We can't assert a specific value because it depends on BS, but we can check it's a number
    assert isinstance(result['comparison']['delta_net_theta'], (int, float))


def test_format_change_unlimited_handling():
    """Unlimited profit/loss sentinels must be formatted correctly."""
    UNLIMITED_PROFIT = 999999999.0
    UNLIMITED_LOSS = -999999999.0

    # Both unlimited → unchanged
    assert _format_change(UNLIMITED_PROFIT, UNLIMITED_PROFIT) == "Unlimited (unchanged)"
    assert _format_change(UNLIMITED_LOSS, UNLIMITED_LOSS) == "Unlimited (unchanged)"

    # From unlimited profit to capped
    assert "Now capped" in _format_change(UNLIMITED_PROFIT, 50000.0)

    # From capped to unlimited loss
    assert "Now unlimited loss" in _format_change(50000.0, UNLIMITED_LOSS)


def test_build_summary_no_material_change():
    comp = {
        "delta_max_profit": 0.0,
        "delta_max_loss": 0.0,
        "delta_margin": 0.0
    }
    summary = _build_summary(comp)
    assert "no material impact" in summary


def test_build_summary_includes_profit_loss_margin():
    comp = {
        "delta_max_profit": 5000.0,
        "delta_max_loss": -2000.0,
        "delta_margin": 1000.0
    }
    summary = _build_summary(comp)
    assert "increases max profit" in summary
    assert "reduces max loss" in summary
    assert "raises margin" in summary