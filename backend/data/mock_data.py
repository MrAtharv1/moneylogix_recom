"""
mock_data.py — Hardcoded realistic option chain data for demo/fallback.

This data is used when all other data sources fail. It represents a
realistic Nifty/BankNifty option chain snapshot. Values are internally consistent.
"""
import math

def _generate_mock_strikes(spot: float, step: int, num_strikes: int, base_iv: float) -> list:
    strikes = []
    half_strikes = num_strikes // 2
    start_strike = (int(spot) // step) * step - (half_strikes * step)
    
    for i in range(num_strikes):
        strike = start_strike + (i * step)
        distance = strike - spot
        
        # IV Smile: Lowest at ATM, increases further away
        strike_iv = base_iv + (abs(distance) / spot) * 0.8
        
        # Mock pricing logic to ensure monotonic changes and ATM straddle target
        # ATM straddle target ~ 1.8% of spot (approx 350 for 19000)
        atm_price = spot * 0.0092 
        
        # Call price decreases as strike increases
        intrinsic_call = max(0.0, spot - strike)
        time_value_call = atm_price * math.exp(-abs(distance) / (step * 3))
        call_ltp = round(intrinsic_call + time_value_call, 2)
        
        # Put price increases as strike increases
        intrinsic_put = max(0.0, strike - spot)
        time_value_put = atm_price * math.exp(-abs(distance) / (step * 3))
        put_ltp = round(intrinsic_put + time_value_put, 2)

        # Spread logic
        spread_multiplier = 1 + (abs(distance) / (step * 10))
        
        # Delta logic
        call_delta = max(0.01, min(0.99, 0.5 - (distance / (step * 10))))
        put_delta = call_delta - 1.0

        # OI and Volume peak at ATM and major round numbers
        oi_multiplier = max(0.1, 1.0 - (abs(distance) / (step * 5)))
        base_oi = 150000 if i % 5 == 0 else 50000

        strikes.append({
            "strike": float(strike),
            "call": {
                "ltp": call_ltp,
                "bid": round(call_ltp * 0.98, 2),
                "ask": round(call_ltp * 1.02 + (1.5 * spread_multiplier), 2),
                "oi": int(base_oi * oi_multiplier),
                "volume": int(base_oi * oi_multiplier * 1.5),
                "iv": round(strike_iv, 4),
                "delta": round(call_delta, 2),
                "theta": -15.5,
                "gamma": 0.002,
                "vega": 12.0
            },
            "put": {
                "ltp": put_ltp,
                "bid": round(put_ltp * 0.98, 2),
                "ask": round(put_ltp * 1.02 + (1.5 * spread_multiplier), 2),
                "oi": int(base_oi * oi_multiplier * 0.9),
                "volume": int(base_oi * oi_multiplier * 1.4),
                "iv": round(strike_iv, 4),
                "delta": round(put_delta, 2),
                "theta": -14.2,
                "gamma": 0.002,
                "vega": 12.0
            }
        })
    return strikes

def get_option_chain(symbol: str) -> dict:
    """
    Returns full option chain in internal format.
    Supports: "NIFTY", "BANKNIFTY" (case-insensitive).
    Returns NIFTY data for unknown symbols.
    """
    sym = symbol.upper()
    
    if sym == "BANKNIFTY":
        spot = 44000.0
        lot_size = 15
        step = 200
        atm_straddle = 800.0
        current_iv = 0.165
    else: # Default NIFTY
        sym = "NIFTY"
        spot = 19000.0
        lot_size = 50
        step = 100
        atm_straddle = 350.0
        current_iv = 0.138

    return {
        "symbol": sym,
        "spot": spot,
        "timestamp": "2024-07-01T10:30:00",
        "expiry": "2024-07-25",
        "days_to_expiry": 24,
        "iv_rank": 42.0,
        "current_iv": current_iv,
        "iv_52w_high": 0.28,
        "iv_52w_low": 0.09,
        "atm_straddle_price": atm_straddle,
        "lot_size": lot_size,
        "strikes": _generate_mock_strikes(spot, step, 21, current_iv)
    }