"""
tests/test_fallback.py — Tests the 4‑tier data cascade.
"""
import sys
import os
import pytest

# Point to the backend folder
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from data.fallback import get_option_chain


def test_fallback_returns_valid_structure():
    """Ensures the fallback always returns a (chain, mode) tuple with valid data."""
    data, mode = get_option_chain('NIFTY')

    # The chain must be a dict
    assert isinstance(data, dict), "Chain must be a dict"

    # Must have required top‑level keys
    required_keys = {'symbol', 'spot', 'strikes', 'days_to_expiry', 'current_iv'}
    assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - set(data.keys())}"

    # Spot must be a positive number
    assert data['spot'] > 0, f"Spot must be > 0, got {data['spot']}"

    # Strikes must be a non‑empty list
    assert isinstance(data['strikes'], list), "Strikes must be a list"
    assert len(data['strikes']) > 0, "Strikes list cannot be empty"

    # Check a random strike for required option fields
    sample = data['strikes'][0]
    assert 'strike' in sample, "Strike missing 'strike' field"
    assert 'call' in sample, "Strike missing 'call' field"
    assert 'put' in sample, "Strike missing 'put' field"
    assert 'ltp' in sample['call'], "Call missing 'ltp'"
    assert 'ltp' in sample['put'], "Put missing 'ltp'"

    # Mode must be one of the 4 allowed values
    assert mode in ('live', 'cached', 'snapshot', 'demo'), f"Invalid mode: {mode}"

    # Symbol should be uppercase
    assert data['symbol'] == data['symbol'].upper(), "Symbol must be uppercase"


def test_fallback_case_insensitive():
    """'nifty' and 'NIFTY' should return the same data (cache key normalisation)."""
    data1, _ = get_option_chain('NIFTY')
    data2, _ = get_option_chain('nifty')
    assert data1['symbol'] == data2['symbol'] == 'NIFTY'
    # Spot should match
    assert data1['spot'] == data2['spot']