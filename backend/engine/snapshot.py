"""snapshot.py — Strategy state persistence for health monitoring."""
import uuid
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

_DB = {}
_HISTORY = {}
_DB_LOCK = asyncio.Lock()
_HISTORY_LOCK = asyncio.Lock()

async def create_strategy_snapshot(legs: list[dict], metrics: dict, symbol: str,
                                   strategy_type: str, spot: float, iv: float,
                                   chain: dict | None = None) -> str:
    strategy_id = str(uuid.uuid4())
    portfolio_delta = (metrics.get("portfolio_greeks") or {}).get("net_delta", 0.0)
    days_to_expiry = metrics.get("days_to_expiry", 30)

    async with _DB_LOCK:
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
        
    async with _HISTORY_LOCK:
        _HISTORY[strategy_id] = []

    logger.info(f"Saved snapshot {strategy_id} to RAM")

    try:
        from database import save_snapshot
        db_metrics = dict(metrics)
        if chain is not None:
            db_metrics["full_chain"] = chain
        # Await the async DB call so we don't block the loop
        await save_snapshot(strategy_id, symbol, strategy_type, legs, db_metrics, spot, iv)
    except Exception:
        logger.exception(f"SQLite dual-write failed for {strategy_id}")

    return strategy_id

async def get_entry_state(strategy_id: str) -> dict | None:
    async with _DB_LOCK:
        return _DB.get(strategy_id)

async def log_health_event(strategy_id: str, diff: dict, explanation: str) -> None:
    async with _HISTORY_LOCK:
        if strategy_id not in _HISTORY:
            _HISTORY[strategy_id] = []
        _HISTORY[strategy_id].append({
            "diff": diff,
            "explanation": explanation,
            "timestamp": datetime.utcnow().isoformat(),
            "checked_at": datetime.utcnow().isoformat()
        })

    try:
        from database import save_health_log
        await save_health_log(strategy_id, diff, explanation)
    except Exception:
        logger.exception(f"SQLite dual-write failed for health log {strategy_id}")

async def get_health_history(strategy_id: str) -> list[dict]:
    async with _HISTORY_LOCK:
        logs = _HISTORY.get(strategy_id, [])
        return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)