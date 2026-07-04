"""
tests/test_strategy_builder.py — Tests the main orchestration module.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from engine.strategy_builder import build_strategy_metrics, _safe_default_metrics


# ─── Fixture: mock option chain ──────────────────────────────────────────────
@pytest.fixture
def mock_chain():
    return {
        "symbol": "NIFTY",
        "spot": 19000.0,
        "days_to_expiry": 30,
        "current_iv": 0.15,
        "iv_52w_high": 0.28,
        "iv_52w_low": 0.09,
        "strikes": [
            {
                "strike": 19000,
                "call": {"ltp": 378.0, "bid": 376.0, "ask": 380.0, "oi": 150000, "volume": 20000, "iv": 0.15},
                "put": {"ltp": 375.0, "bid": 373.0, "ask": 377.0, "oi": 120000, "volume": 18000, "iv": 0.15}
            },
            {
                "strike": 19500,
                "call": {"ltp": 200.0, "bid": 198.0, "ask": 202.0, "oi": 80000, "volume": 10000, "iv": 0.16},
                "put": {"ltp": 550.0, "bid": 548.0, "ask": 552.0, "oi": 90000, "volume": 12000, "iv": 0.16}
            }
        ]
    }


def make_leg(strike, option_type="call", side="buy", qty=1, lot=65, iv=0.15):
    return {
        "id": f"leg-{strike}",
        "strike": strike,
        "option_type": option_type,
        "side": side,
        "quantity": qty,
        "lot_size": lot,
        "iv": iv,
    }


# ─── Tests ────────────────────────────────────────────────────────────────────

@patch('engine.strategy_builder.get_option_chain')
def test_build_strategy_metrics_returns_correct_keys(mock_get_chain, mock_chain):
    """Ensures the returned metrics dict has all expected keys with correct structure."""
    mock_get_chain.return_value = (mock_chain, "live")

    legs = [make_leg(19000, "call", "buy")]
    metrics, mode = build_strategy_metrics(legs, "NIFTY")

    # Top‑level keys must match _safe_default_metrics + risk_score
    expected_keys = {
        'legs', 'greeks_per_leg', 'portfolio_greeks', 'risk_metrics',
        'liquidity', 'payoff_curve', 'iv_rank', 'expected_move_pct', 'risk_score'
    }
    assert expected_keys.issubset(set(metrics.keys())), f"Missing keys: {expected_keys - set(metrics.keys())}"

    # Portfolio Greeks must have net_delta, net_theta, etc.
    pg = metrics['portfolio_greeks']
    assert 'net_delta' in pg, "portfolio_greeks missing 'net_delta'"
    assert 'net_theta' in pg, "portfolio_greeks missing 'net_theta'"
    assert 'leg_contributions' in pg, "portfolio_greeks missing 'leg_contributions'"

    # Risk metrics must have max_profit, max_loss, breakevens, etc.
    rm = metrics['risk_metrics']
    assert 'max_profit' in rm
    assert 'max_loss' in rm
    assert 'breakevens' in rm
    assert 'probability_of_profit' in rm
    assert 'margin_required' in rm

    # Legs should have entry_price (critical fix)
    assert len(metrics['legs']) > 0, "Legs list is empty"
    assert 'entry_price' in metrics['legs'][0], "Leg missing 'entry_price'"
    assert metrics['legs'][0]['entry_price'] > 0, "entry_price must be positive"

    # Mode should be 'live' (from mock)
    assert mode == 'live'


@patch('engine.strategy_builder.get_option_chain')
def test_build_strategy_metrics_fallback_on_chain_failure(mock_get_chain):
    """If the chain fetch fails, returns a safe default dict without crashing."""
    mock_get_chain.side_effect = Exception("Network error")

    legs = [make_leg(19000)]
    metrics, mode = build_strategy_metrics(legs, "NIFTY")

    # Should still return a dict with default values
    assert isinstance(metrics, dict)
    assert metrics['legs'] == []  # No legs computed
    assert metrics['portfolio_greeks']['net_delta'] == 0.0
    assert mode == 'unavailable'  # The error mode


@patch('engine.strategy_builder.get_option_chain')
def test_build_strategy_metrics_calculates_risk_score(mock_get_chain, mock_chain):
    """Ensures the hybrid risk score is computed and has the required fields."""
    mock_get_chain.return_value = (mock_chain, "live")

    legs = [make_leg(19000, "call", "buy"), make_leg(19500, "call", "sell")]
    metrics, _ = build_strategy_metrics(legs, "NIFTY")

    rs = metrics.get('risk_score')
    assert rs is not None, "risk_score should not be None"
    assert 'score' in rs, "risk_score missing 'score'"
    assert 'tier' in rs, "risk_score missing 'tier'"
    assert 'color' in rs, "risk_score missing 'color'"
    assert 'breakdown' in rs, "risk_score missing 'breakdown'"
    assert 'interpretation' in rs, "risk_score missing 'interpretation'"
    assert 0 <= rs['score'] <= 100, f"Score must be 0-100, got {rs['score']}"


def test_safe_default_metrics_has_correct_keys():
    """Sanity check: the default metrics dict must have the correct keys."""
    dm = _safe_default_metrics()
    assert 'portfolio_greeks' in dm
    assert 'net_delta' in dm['portfolio_greeks']
    assert 'leg_contributions' in dm['portfolio_greeks']
    # Ensure no phantom 'rho' key exists
    assert 'rho' not in dm['portfolio_greeks'], "phantom 'rho' key found!"