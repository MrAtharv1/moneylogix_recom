"""
tests/test_health_monitor.py — Tests the diff computation and thresholds.
"""
import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from engine.health_monitor import compute_health_diff


def test_compute_health_diff_no_changes():
    """If entry and current are identical, has_changes must be False."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}

    diff = compute_health_diff(entry, current)
    assert diff["has_changes"] is False
    assert diff["iv"] is None
    assert diff["price"] is None
    assert diff["pnl"] is None
    assert diff["delta"] is None
    assert diff["dte_warning"] is False  # 30 >= 7


def test_compute_health_diff_iv_change_triggers():
    """IV change of >= 1.0 percentage point must be detected."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.165, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}  # +1.5pp

    diff = compute_health_diff(entry, current)
    assert diff["has_changes"] is True
    assert diff["iv"] is not None
    assert diff["iv"]["change"] == 0.015  # 1.5 percentage points
    assert diff["iv"]["direction"] == "up"
    assert "1.5pp" in diff["iv"]["label"]


def test_compute_health_diff_iv_change_below_threshold():
    """Small IV changes (< 1.0pp) must be ignored."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.152, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}  # +0.2pp

    diff = compute_health_diff(entry, current)
    assert diff["iv"] is None
    assert diff["has_changes"] is False


def test_compute_health_diff_price_change_triggers():
    """Price change of >= 0.5% must be detected."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.15, "spot": 19100, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}  # +0.53%

    diff = compute_health_diff(entry, current)
    assert diff["has_changes"] is True
    assert diff["price"] is not None
    assert abs(diff["price"]["pct"] - 0.53) < 0.01
    assert "0.5%" in diff["price"]["label"]


def test_compute_health_diff_pnl_change_triggers():
    """PnL change of >= ₹100 must be detected."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.15, "spot": 19000, "pnl": 150.0, "portfolio_delta": 0.5, "days_to_expiry": 30}

    diff = compute_health_diff(entry, current)
    assert diff["has_changes"] is True
    assert diff["pnl"] is not None
    assert diff["pnl"]["change"] == 150.0


def test_compute_health_diff_delta_change_triggers():
    """Delta change of >= 0.05 must be detected."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.57, "days_to_expiry": 30}

    diff = compute_health_diff(entry, current)
    assert diff["has_changes"] is True
    assert diff["delta"] is not None
    assert diff["delta"]["change"] == 0.07


def test_compute_health_diff_dte_warning():
    """When DTE < 7, dte_warning must be True."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 5}

    diff = compute_health_diff(entry, current)
    assert diff["dte_warning"] is True


def test_compute_health_diff_multiple_changes():
    """Multiple changes should all be captured."""
    entry = {"iv": 0.15, "spot": 19000, "pnl": 0.0, "portfolio_delta": 0.5, "days_to_expiry": 30}
    current = {"iv": 0.17, "spot": 19150, "pnl": 200.0, "portfolio_delta": 0.6, "days_to_expiry": 30}

    diff = compute_health_diff(entry, current)
    assert diff["has_changes"] is True
    assert diff["iv"] is not None
    assert diff["price"] is not None
    assert diff["pnl"] is not None
    assert diff["delta"] is not None