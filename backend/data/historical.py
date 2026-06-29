"""
historical.py — Historical IV data for IV Rank computation.
Uses India VIX as a proxy for Nifty IV.
"""
import yfinance as yf
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

FALLBACK_IV_DATA = {
    "current_iv": 0.138,
    "iv_52w_high": 0.28,
    "iv_52w_low": 0.09,
    "iv_rank": 32.0,
    "historical_ivs": []
}

def get_historical_iv(symbol: str = "NIFTY", lookback_days: int = 365) -> dict:
    """
    Fetches historical India VIX data via yfinance.
    On ANY failure: return FALLBACK_IV_DATA (never raise).
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # yfinance India VIX ticker
        vix_data = yf.download("^INDIAVIX", start=start_date, end=end_date, progress=False)
        
        if vix_data.empty:
            raise ValueError("No data returned from yfinance")
            
        # Get Closing prices and drop NaNs
        closes = vix_data['Close'].dropna().tolist()
        if not closes:
            raise ValueError("No closing data found")
            
        current_iv_pct = closes[-1]
        high_iv_pct = max(closes)
        low_iv_pct = min(closes)
        
        # IV Rank formula: (Current - Low) / (High - Low) * 100
        if high_iv_pct > low_iv_pct:
            iv_rank = ((current_iv_pct - low_iv_pct) / (high_iv_pct - low_iv_pct)) * 100.0
        else:
            iv_rank = 50.0

        return {
            "current_iv": current_iv_pct / 100.0,
            "iv_52w_high": high_iv_pct / 100.0,
            "iv_52w_low": low_iv_pct / 100.0,
            "iv_rank": round(iv_rank, 2),
            "historical_ivs": [round(x / 100.0, 4) for x in closes]
        }
        
    except Exception as e:
        logger.warning(f"Failed to fetch historical IV for {symbol}: {e}. Using fallback.")
        return FALLBACK_IV_DATA