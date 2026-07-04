"""
fallback.py — 4-tier data cascade for option chain data.
Handles all fallback logic transparently so the UI never crashes.
"""
import logging
from data.nse_fetcher import fetch_option_chain, DataFetchError
from data.cache import option_chain_cache
from data.mock_data import get_option_chain as get_mock_chain

logger = logging.getLogger(__name__)

async def get_option_chain(symbol: str) -> tuple[dict, str]:
    """
    Returns (chain_data, data_mode).
    data_mode is one of: "live", "cached", "snapshot", "demo"
    NEVER raises. NEVER returns None.
    """
    
    # Tier 1: Live (Async)
    try:
        data = await fetch_option_chain(symbol)
        await option_chain_cache.set(symbol, data)
        logger.info(f"Data tier: live for {symbol}")
        return data, "live"
    except (DataFetchError, Exception) as e:
        logger.warning(f"NSE fetch failed for {symbol}: {e}")
    
    # Tier 2: Cache (Async)
    cached = await option_chain_cache.get(symbol)
    if cached:
        logger.info(f"Data tier: cached for {symbol}")
        return cached, "cached"
    
    # Tier 3: DB snapshot (Async)
    try:
        # Import lazily to avoid circular imports
        from database import get_last_option_data 
        snapshot = await get_last_option_data(symbol)
        if snapshot:
            logger.info(f"Data tier: snapshot for {symbol}")
            return snapshot, "snapshot"
    except Exception as e:
        logger.warning(f"DB snapshot failed for {symbol}: {e}")
    
    # Tier 4: Mock (always works, synchronous data generation)
    logger.info(f"Data tier: demo for {symbol}")
    return get_mock_chain(symbol), "demo"