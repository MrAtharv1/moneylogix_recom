"""
snapshot.py — Strategy state persistence for health monitoring.
HACKATHON EDITION: Uses ultra-fast, bulletproof in-memory RAM storage 
to bypass Windows SQLite file-permission and schema errors.
"""

import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Bulletproof RAM Storage
_DB = {}
_HISTORY = {}

def create_strategy_snapshot(
    legs: list[dict],
    metrics: dict,
    symbol: str,
    strategy_type: str,
    spot: float,
    iv: float,
) -> str:
    strategy_id = str(uuid.uuid4())

    portfolio_delta = (metrics.get("portfolio_greeks") or {}).get("net_delta", 0.0)
    days_to_expiry = metrics.get("days_to_expiry", 30)

    # Store directly in RAM
    _DB[strategy_id] = {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "strategy_type": strategy_type,
        "legs": legs,
        "entry_state": {
            "iv": iv,
            "spot": spot,
            "pnl": 0.0,
            "portfolio_delta": portfolio_delta,
            "days_to_expiry": days_to_expiry,
        },
    }
    _HISTORY[strategy_id] = []
    
    logger.info(f"Successfully saved snapshot {strategy_id} to RAM")
    return strategy_id

def get_entry_state(strategy_id: str) -> dict | None:
    return _DB.get(strategy_id)

def log_health_event(strategy_id: str, diff: dict, explanation: str) -> None:
    if strategy_id not in _HISTORY:
        _HISTORY[strategy_id] = []
        
    _HISTORY[strategy_id].append({
        "diff": diff,
        "explanation": explanation,
        "timestamp": datetime.utcnow().isoformat(),
        "checked_at": datetime.utcnow().isoformat()
    })

def get_health_history(strategy_id: str) -> list[dict]:
    logs = _HISTORY.get(strategy_id, [])
    # Sort newest first
    return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)