"""historical.py — Historical IV data for IV Rank computation."""
import yfinance as yf
import logging
import pandas as pd
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

FALLBACK_IV_DATA = {
    "current_iv": 0.138,
    "iv_52w_high": 0.28,
    "iv_52w_low": 0.09,
    "iv_rank": 32.0,
    "historical_ivs": []
}

def _fetch_yfinance_sync(symbol: str, lookback_days: int) -> dict:
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    vix = yf.download("^INDIAVIX", start=start, end=end, progress=False)
    
    if vix.empty:
        raise ValueError("No VIX data")
        
    if isinstance(vix.columns, pd.MultiIndex):
        close = vix['Close']
    else:
        close = vix['Close']
        
    closes = close.dropna().tolist()
    if not closes:
        raise ValueError("No closing data")
        
    current = closes[-1]
    high = max(closes)
    low = min(closes)
    iv_rank = ((current - low) / (high - low)) * 100 if high > low else 50.0
    
    return {
        "current_iv": float(current / 100.0),
        "iv_52w_high": float(high / 100.0),
        "iv_52w_low": float(low / 100.0),
        "iv_rank": round(iv_rank, 2),
        "historical_ivs": [round(float(x) / 100.0, 4) for x in closes]
    }

async def get_historical_iv(symbol: str = "NIFTY", lookback_days: int = 365) -> dict:
    try:
        # Prevent pandas and yfinance from blocking the async event loop
        return await asyncio.to_thread(_fetch_yfinance_sync, symbol, lookback_days)
    except Exception as e:
        logger.warning(f"Historical IV fetch failed: {e}")
        return FALLBACK_IV_DATA