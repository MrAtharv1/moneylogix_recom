"""
tests/test_snapshot.py — Tests in‑memory persistence and dual‑write.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_path)

from engine.snapshot import (
    create_strategy_snapshot,
    get_entry_state,
    log_health_event,
    get_health_history,
    _DB,
    _HISTORY,
    _DB_LOCK,
    _HISTORY_LOCK
)


def test_create_and_retrieve_snapshot():
    """Creating a snapshot stores it in the in‑memory _DB."""
    legs = [{"id": "leg1", "strike": 19000}]
    metrics = {"portfolio_greeks": {"net_delta": 0.5}, "days_to_expiry": 30}
    strategy_id = create_strategy_snapshot(legs, metrics, "NIFTY", "iron_condor", 19000.0, 0.15)

    # Retrieve it
    entry = get_entry_state(strategy_id)
    assert entry is not None
    assert entry["strategy_id"] == strategy_id
    assert entry["symbol"] == "NIFTY"
    assert entry["strategy_type"] == "iron_condor"
    assert entry["legs"] == legs
    assert entry["entry_state"]["iv"] == 0.15
    assert entry["entry_state"]["spot"] == 19000.0
    assert entry["entry_state"]["portfolio_delta"] == 0.5


def test_get_entry_state_not_found():
    """Non‑existent strategy returns None, not crash."""
    assert get_entry_state("non-existent-id") is None


def test_log_and_retrieve_health_history():
    """Logging health events appends them to the history list."""
    strategy_id = "test-strategy-123"
    diff1 = {"has_changes": True, "iv": {"change": 0.01}}
    diff2 = {"has_changes": False}

    # Log two events
    log_health_event(strategy_id, diff1, "Explanation 1")
    log_health_event(strategy_id, diff2, "")

    history = get_health_history(strategy_id)
    assert len(history) == 2
    assert history[0]["diff"] == diff2  # Newest first (sorted by timestamp)
    assert history[0]["explanation"] == ""
    assert history[1]["diff"] == diff1
    assert history[1]["explanation"] == "Explanation 1"


def test_get_health_history_empty():
    """Non‑existent strategy returns an empty list."""
    assert get_health_history("non-existent") == []


@patch('engine.snapshot._db_save_snapshot')
@patch('engine.snapshot._db_save_health_log')
def test_dual_write_failure_does_not_crash(mock_db_log, mock_db_save):
    """Even if SQLite write fails, the RAM write succeeds and the app continues."""
    mock_db_save.side_effect = Exception("SQLite write failed")
    mock_db_log.side_effect = Exception("SQLite log failed")

    # This should not raise any exception
    strategy_id = create_strategy_snapshot([], {}, "NIFTY", "custom", 19000.0, 0.15)
    assert get_entry_state(strategy_id) is not None  # RAM write succeeded

    log_health_event(strategy_id, {"has_changes": True}, "Test")
    assert len(get_health_history(strategy_id)) == 1  # RAM log succeeded