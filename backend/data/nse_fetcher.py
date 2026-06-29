"""
nse_fetcher.py — Fetch live option chain from NSE public API.
"""
import httpx
import logging
from datetime import datetime

# Mock config import based on instructions
try:
    from config import settings
    NSE_TIMEOUT = settings.NSE_TIMEOUT_SECONDS
except ImportError:
    NSE_TIMEOUT = 3.0

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

class DataFetchError(Exception):
    """Raised when NSE data cannot be fetched for any reason."""
    pass

def normalize_nse_response(raw: dict, symbol: str) -> dict:
    """Normalizes NSE API response structure to match mock_data.py structure."""
    try:
        records = raw["records"]
        spot = records["underlyingValue"]
        expiry_dates = records["expiryDates"]
        if not expiry_dates:
            raise ValueError("No expiry dates found in NSE payload")
            
        target_expiry = expiry_dates[0]  # Front month expiry
        
        strikes_data = []
        for item in records["data"]:
            if item.get("expiryDate") == target_expiry:
                strike_prc = float(item["strikePrice"])
                
                # Helper to safely extract CE/PE data
                def extract_leg(leg_data):
                    if not leg_data:
                        return {
                            "ltp": 0.0, "bid": 0.0, "ask": 0.0, "oi": 0, "volume": 0,
                            "iv": 0.0, "delta": 0.0, "theta": 0.0, "gamma": 0.0, "vega": 0.0
                        }
                    return {
                        "ltp": float(leg_data.get("lastPrice", 0)),
                        "bid": float(leg_data.get("bidprice", 0)), # typical NSE key
                        "ask": float(leg_data.get("askPrice", 0)),
                        "oi": int(leg_data.get("openInterest", 0)),
                        "volume": int(leg_data.get("totalTradedVolume", 0)),
                        "iv": float(leg_data.get("impliedVolatility", 0)) / 100.0, # convert % to decimal
                        "delta": float(leg_data.get("delta", 0) or 0),
                        "theta": float(leg_data.get("theta", 0) or 0),
                        "gamma": float(leg_data.get("gamma", 0) or 0),
                        "vega": float(leg_data.get("vega", 0) or 0)
                    }

                ce_data = extract_leg(item.get("CE"))
                pe_data = extract_leg(item.get("PE"))
                
                strikes_data.append({
                    "strike": strike_prc,
                    "call": ce_data,
                    "put": pe_data
                })

        # Find ATM Straddle
        closest_strike = min(strikes_data, key=lambda x: abs(x["strike"] - spot))
        atm_straddle = closest_strike["call"]["ltp"] + closest_strike["put"]["ltp"]

        return {
            "symbol": symbol.upper(),
            "spot": spot,
            "timestamp": datetime.utcnow().isoformat(),
            "expiry": target_expiry,
            "days_to_expiry": 1, # Placeholder, would need date math here
            "iv_rank": 50.0,     # Placeholder, populated elsewhere usually
            "current_iv": closest_strike["call"]["iv"],
            "iv_52w_high": 0.0,  # Placeholder
            "iv_52w_low": 0.0,   # Placeholder
            "atm_straddle_price": atm_straddle,
            "lot_size": 50 if symbol.upper() == "NIFTY" else 15,
            "strikes": strikes_data
        }
    except KeyError as e:
        raise DataFetchError(f"Missing expected key in NSE response: {e}")
    except Exception as e:
        raise DataFetchError(f"Failed to normalize NSE response: {e}")

def fetch_option_chain(symbol: str) -> dict:
    """Fetches live option chain from NSE and normalizes to internal format."""
    base_url = "https://www.nseindia.com/"
    api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
    
    try:
        with httpx.Client(headers=NSE_HEADERS, timeout=NSE_TIMEOUT) as client:
            # Step 2: GET home page to obtain session cookies
            client.get(base_url)
            
            # Step 3: GET actual API
            response = client.get(api_url)
            response.raise_for_status()
            
            raw_data = response.json()
            
            # Step 4: Normalize
            return normalize_nse_response(raw_data, symbol)
            
    except Exception as e:
        # Wrap any network, JSON, or formatting exception and raise explicitly
        raise DataFetchError(f"NSE Fetch Error: {str(e)}")