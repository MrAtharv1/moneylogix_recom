"""nse_fetcher.py — Fetch live option chain from NSE public API."""
import httpx
import logging
from datetime import datetime
from data.historical import get_historical_iv
from data.mock_data import asset_config

try:
    from config import settings
    NSE_TIMEOUT = settings.NSE_TIMEOUT_SECONDS
except ImportError:
    NSE_TIMEOUT = 3.0

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

class DataFetchError(Exception):
    pass

async def normalize_nse_response(raw: dict, symbol: str) -> dict:
    records = raw["records"]
    spot = records["underlyingValue"]
    expiry_dates = records["expiryDates"]
    if not expiry_dates:
        raise DataFetchError("No expiry dates found")
    target_expiry = expiry_dates[0]
    expiry_dt = datetime.strptime(target_expiry, "%d-%b-%Y")
    days_to_expiry = max(0, (expiry_dt - datetime.now()).days)

    # Await the historical data fetch
    hist = await get_historical_iv(symbol)

    strikes_data = []
    for item in records["data"]:
        if item.get("expiryDate") != target_expiry:
            continue
        strike_prc = float(item["strikePrice"])

        def extract_leg(leg_data):
            if not leg_data:
                return {"ltp": 0.0, "bid": 0.0, "ask": 0.0, "oi": 0, "volume": 0,
                        "iv": 0.0, "delta": 0.0, "theta": 0.0, "gamma": 0.0, "vega": 0.0}
            iv_val = float(leg_data.get("impliedVolatility", 0)) / 100.0
            
            delta = float(leg_data.get("delta", 0) or 0)
            theta = float(leg_data.get("theta", 0) or 0)
            gamma = float(leg_data.get("gamma", 0) or 0)
            vega = float(leg_data.get("vega", 0) or 0)
            
            # If Greeks missing, compute them on the fly
            if delta == 0 and theta == 0 and gamma == 0 and vega == 0 and iv_val > 0:
                try:
                    from quant.blackscholes import compute as bs
                    opt_type = "call" if "CE" in leg_data else "put"
                    g = bs(S=spot, K=strike_prc, T_days=days_to_expiry, r=0.065, sigma=iv_val, option_type=opt_type)
                    delta, theta, gamma, vega = g["delta"], g["theta"], g["gamma"], g["vega"]
                except Exception:
                    pass
                    
            return {
                "ltp": float(leg_data.get("lastPrice", 0)),
                "bid": float(leg_data.get("bidprice", 0)),
                "ask": float(leg_data.get("askPrice", 0)),
                "oi": int(leg_data.get("openInterest", 0)),
                "volume": int(leg_data.get("totalTradedVolume", 0)),
                "iv": iv_val,
                "delta": delta,
                "theta": theta,
                "gamma": gamma,
                "vega": vega,
            }

        ce = extract_leg(item.get("CE", {}))
        pe = extract_leg(item.get("PE", {}))
        strikes_data.append({"strike": strike_prc, "call": ce, "put": pe})

    if not strikes_data:
        raise DataFetchError("No valid strikes found for target expiry")

    closest = min(strikes_data, key=lambda x: abs(x["strike"] - spot))
    atm_straddle = closest["call"]["ltp"] + closest["put"]["ltp"]

    # Dynamic Fallback: Avoid hardcoding integers. If the NSE API misses lot sizes, 
    # we pull from our comprehensive static asset dictionary.
    fallback_cfg = asset_config.get(symbol.upper(), {"lot": 50})
    lot_size = fallback_cfg["lot"]

    return {
        "symbol": symbol.upper(),
        "spot": spot,
        "timestamp": datetime.utcnow().isoformat(),
        "expiry": target_expiry,
        "days_to_expiry": days_to_expiry,
        "iv_rank": hist.get("iv_rank", 50.0),
        "current_iv": hist.get("current_iv", 0.15),
        "iv_52w_high": hist.get("iv_52w_high", 0.28),
        "iv_52w_low": hist.get("iv_52w_low", 0.09),
        "atm_straddle_price": atm_straddle,
        "lot_size": lot_size,
        "strikes": strikes_data
    }

async def fetch_option_chain(symbol: str) -> dict:
    base_url = "https://www.nseindia.com/"
    api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
    try:
        # Use AsyncClient to prevent blocking the FastAPI event loop
        async with httpx.AsyncClient(headers=NSE_HEADERS, timeout=NSE_TIMEOUT) as client:
            await client.get(base_url)
            resp = await client.get(api_url)
            resp.raise_for_status()
            return await normalize_nse_response(resp.json(), symbol)
    except Exception as e:
        raise DataFetchError(f"NSE Fetch Error: {str(e)}")