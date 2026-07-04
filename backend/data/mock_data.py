"""mock_data.py — Hardcoded realistic option chain data for demo/fallback."""
import math
from datetime import datetime, timedelta

# ─── YOUR FULL ASSET CONFIG (keep as is) ─────────────────────────────────────
asset_config = {
    "LTFIN": {'spot': 315.4, 'lot': 2250, 'step': 5.0},
    "MCDOWELL": {'spot': 1375.2, 'lot': 400, 'step': 10.0},
    "MCDOWELLS": {'spot': 1375.2, 'lot': 400, 'step': 10.0},
    "UNITEDSPIRITS": {'spot': 1375.2, 'lot': 400, 'step': 10.0},
    "LTIM": {'spot': 3672.0, 'lot': 150, 'step': 50.0},
    "LICHOUSING": {'spot': 548.65, 'lot': 1000, 'step': 10.0},
    "POLICYBAZAAR": {'spot': 1682.6, 'lot': 350, 'step': 20.0},
    "MOTHERSONS": {'spot': 148.62, 'lot': 6150, 'step': 1.0},
    "INDIGOAIR": {'spot': 5486.0, 'lot': 150, 'step': 50.0},
    "VEDANTA": {'spot': 277.95, 'lot': 1150, 'step': 5.0},
    "LTFINANCE": {'spot': 315.4, 'lot': 2250, 'step': 5.0},
    "BAJAJFINANCE": {'spot': 1030.2, 'lot': 750, 'step': 10.0},
    "360ONE": {'spot': 1079.9, 'lot': 500, 'step': 20.0},
    "ABB": {'spot': 6801.0, 'lot': 125, 'step': 100.0},
    "ABCAPITAL": {'spot': 397.4, 'lot': 3100, 'step': 5.0},
    "ADANIENSOL": {'spot': 1570.3, 'lot': 675, 'step': 20.0},
    "ADANIENT": {'spot': 3204.2, 'lot': 309, 'step': 20.0},
    "ADANIGREEN": {'spot': 1571.8, 'lot': 600, 'step': 10.0},
    "ADANIPORTS": {'spot': 1898.6, 'lot': 475, 'step': 20.0},
    "ADANIPOWER": {'spot': 227.02, 'lot': 3550, 'step': 2.5},
    "AIRTEL": {'spot': 1871.6, 'lot': 475, 'step': 20.0},
    "ALKEM": {'spot': 5550.5, 'lot': 125, 'step': 50.0},
    "AMBER": {'spot': 7453.0, 'lot': 100, 'step': 100.0},
    "AMBUJACEM": {'spot': 433.75, 'lot': 1200, 'step': 5.0},
    "ANGELONE": {'spot': 349.9, 'lot': 2500, 'step': 5.0},
    "APLAPOLLO": {'spot': 1801.4, 'lot': 350, 'step': 20.0},
    "APOLLOHOSP": {'spot': 8778.0, 'lot': 125, 'step': 100.0},
    "ASHOKLEY": {'spot': 165.92, 'lot': 5000, 'step': 2.5},
    "ASIANPAINT": {'spot': 2762.1, 'lot': 250, 'step': 20.0},
    "ASTRAL": {'spot': 1332.2, 'lot': 425, 'step': 20.0},
    "AUBANK": {'spot': 1068.1, 'lot': 1000, 'step': 10.0},
    "AUROPHARMA": {'spot': 1576.1, 'lot': 550, 'step': 20.0},
    "AXISBANK": {'spot': 1372.7, 'lot': 625, 'step': 10.0},
    "BAJAJ-AUTO": {'spot': 9833.0, 'lot': 75, 'step': 100.0},
    "BAJAJFIN": {'spot': 1030.2, 'lot': 750, 'step': 10.0},
    "BAJAJFINSV": {'spot': 1872.7, 'lot': 300, 'step': 20.0},
    "BAJAJHLDNG": {'spot': 11027.0, 'lot': 75, 'step': 100.0},
    "BAJFINANCE": {'spot': 1030.2, 'lot': 750, 'step': 10.0},
    "BANDHANBNK": {'spot': 205.85, 'lot': 3600, 'step': 2.5},
    "BANKBARODA": {'spot': 263.15, 'lot': 2925, 'step': 1.5},
    "BANKINDIA": {'spot': 146.7, 'lot': 5200, 'step': 2.5},
    "BANKNIFTY": {'spot': 58649.6, 'lot': 30, 'step': 100.0},
    "BDL": {'spot': 1364.8, 'lot': 425, 'step': 20.0},
    "BEL": {'spot': 419.1, 'lot': 1425, 'step': 5.0},
    "BHARATFORG": {'spot': 2147.2, 'lot': 500, 'step': 20.0},
    "BHARTIARTL": {'spot': 1871.6, 'lot': 475, 'step': 20.0},
    "BHEL": {'spot': 405.05, 'lot': 2625, 'step': 2.5},
    "BIOCON": {'spot': 422.9, 'lot': 2500, 'step': 5.0},
    "BLUESTARCO": {'spot': 1585.7, 'lot': 325, 'step': 20.0},
    "BOSCHLTD": {'spot': 41665.0, 'lot': 25, 'step': 250.0},
    "BPCL": {'spot': 313.05, 'lot': 1975, 'step': 5.0},
    "BRITANNIA": {'spot': 5331.5, 'lot': 125, 'step': 50.0},
    "BSE": {'spot': 3848.0, 'lot': 200, 'step': 50.0},
    "CAMS": {'spot': 796.95, 'lot': 825, 'step': 10.0},
    "CANBK": {'spot': 128.05, 'lot': 6750, 'step': 0.2},
    "CDSL": {'spot': 1342.4, 'lot': 475, 'step': 20.0},
    "CGPOWER": {'spot': 967.25, 'lot': 850, 'step': 20.0},
    "CHOLAFIN": {'spot': 1809.1, 'lot': 625, 'step': 20.0},
    "CIPLA": {'spot': 1470.6, 'lot': 425, 'step': 10.0},
    "COALINDIA": {'spot': 437.75, 'lot': 1350, 'step': 5.0},
    "COCHINSHIP": {'spot': 1494.6, 'lot': 400, 'step': 20.0},
    "COFORGE": {'spot': 1433.8, 'lot': 475, 'step': 20.0},
    "COLPAL": {'spot': 2076.2, 'lot': 275, 'step': 20.0},
    "CONCOR": {'spot': 482.05, 'lot': 1250, 'step': 5.0},
    "CROMPTON": {'spot': 274.0, 'lot': 2150, 'step': 2.5},
    "CUMMINSIND": {'spot': 5593.0, 'lot': 200, 'step': 100.0},
    "DABUR": {'spot': 446.35, 'lot': 1250, 'step': 5.0},
    "DALBHARAT": {'spot': 1764.4, 'lot': 325, 'step': 20.0},
    "DELHIVERY": {'spot': 514.45, 'lot': 2075, 'step': 5.0},
    "DIVISLAB": {'spot': 6722.5, 'lot': 100, 'step': 100.0},
    "DIXON": {'spot': 12481.0, 'lot': 50, 'step': 100.0},
    "DLF": {'spot': 654.95, 'lot': 950, 'step': 5.0},
    "DMART": {'spot': 4169.7, 'lot': 150, 'step': 50.0},
    "DRREDDY": {'spot': 1338.5, 'lot': 625, 'step': 10.0},
    "EICHERMOT": {'spot': 7255.5, 'lot': 100, 'step': 100.0},
    "ETERNAL": {'spot': 282.2, 'lot': 2425, 'step': 2.5},
    "EXIDEIND": {'spot': 419.9, 'lot': 1800, 'step': 2.5},
    "FEDERALBNK": {'spot': 333.9, 'lot': 2500, 'step': 2.5},
    "FINNIFTY": {'spot': 27105.9, 'lot': 60, 'step': 50.0},
    "FORCEMOT": {'spot': 19450.0, 'lot': 25, 'step': 500.0},
    "FORTIS": {'spot': 983.65, 'lot': 775, 'step': 10.0},
    "GAIL": {'spot': 175.63, 'lot': 3550, 'step': 1.0},
    "GLENMARK": {'spot': 2217.0, 'lot': 375, 'step': 20.0},
    "GMRAIRPORT": {'spot': 112.9, 'lot': 6975, 'step': 1.0},
    "GODFRYPHLP": {'spot': 2161.7, 'lot': 275, 'step': 50.0},
    "GODREJCP": {'spot': 1082.5, 'lot': 500, 'step': 10.0},
    "GODREJPROP": {'spot': 1978.5, 'lot': 325, 'step': 20.0},
    "GRASIM": {'spot': 3185.8, 'lot': 250, 'step': 20.0},
    "GVT&D": {'spot': 4835.9, 'lot': 125, 'step': 100.0},
    "HAL": {'spot': 4469.0, 'lot': 150, 'step': 50.0},
    "HAVELLS": {'spot': 1197.0, 'lot': 500, 'step': 10.0},
    "HCL": {'spot': 1063.6, 'lot': 400, 'step': 10.0},
    "HCLTECH": {'spot': 1063.6, 'lot': 400, 'step': 10.0},
    "HDFCAMC": {'spot': 2786.4, 'lot': 300, 'step': 6.0},
    "HDFCBANK": {'spot': 804.9, 'lot': 650, 'step': 5.0},
    "HDFCLIFE": {'spot': 577.75, 'lot': 1100, 'step': 5.0},
    "HEROMOTOCO": {'spot': 4841.8, 'lot': 150, 'step': 50.0},
    "HINDALCO": {'spot': 952.0, 'lot': 700, 'step': 10.0},
    "HINDPETRO": {'spot': 404.2, 'lot': 2025, 'step': 5.0},
    "HINDUNILVR": {'spot': 2235.5, 'lot': 300, 'step': 20.0},
    "HINDZINC": {'spot': 533.05, 'lot': 1225, 'step': 10.0},
    "HYUNDAI": {'spot': 1946.2, 'lot': 275, 'step': 20.0},
    "ICICIBANK": {'spot': 1400.4, 'lot': 700, 'step': 10.0},
    "ICICIGI": {'spot': 1778.6, 'lot': 325, 'step': 20.0},
    "ICICIPRULI": {'spot': 501.4, 'lot': 925, 'step': 5.0},
    "IDEA": {'spot': 14.64, 'lot': 71475, 'step': 1.0},
    "IDFCFIRSTB": {'spot': 80.14, 'lot': 9275, 'step': 1.0},
    "IEX": {'spot': 124.96, 'lot': 4350, 'step': 1.0},
    "INDHOTEL": {'spot': 727.85, 'lot': 1000, 'step': 5.0},
    "INDIANB": {'spot': 822.5, 'lot': 1000, 'step': 10.0},
    "INDIGO": {'spot': 5486.0, 'lot': 150, 'step': 50.0},
    "INDUSINDBK": {'spot': 951.95, 'lot': 700, 'step': 10.0},
    "INDUSTOWER": {'spot': 388.25, 'lot': 1700, 'step': 5.0},
    "INFY": {'spot': 1039.4, 'lot': 400, 'step': 5.0},
    "INOXWIND": {'spot': 90.97, 'lot': 6400, 'step': 1.0},
    "IOC": {'spot': 141.9, 'lot': 4875, 'step': 1.0},
    "IREDA": {'spot': 125.08, 'lot': 4525, 'step': 1.0},
    "IRFC": {'spot': 90.69, 'lot': 5425, 'step': 1.0},
    "ITC": {'spot': 293.05, 'lot': 1725, 'step': 2.5},
    "JINDALSTEL": {'spot': 1054.4, 'lot': 625, 'step': 10.0},
    "JIOFIN": {'spot': 241.71, 'lot': 2350, 'step': 2.5},
    "JSWENERGY": {'spot': 571.8, 'lot': 1075, 'step': 5.0},
    "JSWSTEEL": {'spot': 1229.5, 'lot': 675, 'step': 20.0},
    "JUBLFOOD": {'spot': 433.15, 'lot': 1250, 'step': 5.0},
    "KALYANKJIL": {'spot': 392.35, 'lot': 1350, 'step': 5.0},
    "KAYNES": {'spot': 3124.8, 'lot': 150, 'step': 50.0},
    "KEI": {'spot': 5199.0, 'lot': 175, 'step': 100.0},
    "KFINTECH": {'spot': 853.85, 'lot': 575, 'step': 10.0},
    "KOTAKBANK": {'spot': 402.55, 'lot': 2000, 'step': 2.5},
    "KPITTECH": {'spot': 537.05, 'lot': 775, 'step': 10.0},
    "LAURUSLABS": {'spot': 1540.2, 'lot': 850, 'step': 10.0},
    "LICHSGFIN": {'spot': 548.65, 'lot': 1000, 'step': 10.0},
    "LICI": {'spot': 428.4, 'lot': 1400, 'step': 5.0},
    "LODHA": {'spot': 1010.6, 'lot': 625, 'step': 10.0},
    "LT": {'spot': 4103.3, 'lot': 175, 'step': 20.0},
    "LTF": {'spot': 315.4, 'lot': 2250, 'step': 5.0},
    "LTM": {'spot': 3672.0, 'lot': 150, 'step': 50.0},
    "LUPIN": {'spot': 2404.3, 'lot': 425, 'step': 20.0},
    "M&M": {'spot': 3179.5, 'lot': 200, 'step': 20.0},
    "MAHINDRA": {'spot': 3179.5, 'lot': 200, 'step': 20.0},
    "MANAPPURAM": {'spot': 325.6, 'lot': 3000, 'step': 5.0},
    "MANKIND": {'spot': 2510.1, 'lot': 250, 'step': 20.0},
    "MARICO": {'spot': 862.75, 'lot': 1200, 'step': 10.0},
    "MARUTI": {'spot': 14346.0, 'lot': 50, 'step': 100.0},
    "MAXHEALTH": {'spot': 1133.3, 'lot': 525, 'step': 10.0},
    "MAZDOCK": {'spot': 2567.1, 'lot': 225, 'step': 20.0},
    "MCX": {'spot': 2914.3, 'lot': 225, 'step': 50.0},
    "MFSL": {'spot': 1627.2, 'lot': 400, 'step': 20.0},
    "MIDCPNIFTY": {'spot': 14689.9, 'lot': 120, 'step': 25.0},
    "MOTHERSON": {'spot': 148.62, 'lot': 6150, 'step': 1.0},
    "MOTILALOFS": {'spot': 968.4, 'lot': 775, 'step': 10.0},
    "MPHASIS": {'spot': 2265.3, 'lot': 275, 'step': 20.0},
    "MUTHOOTFIN": {'spot': 2972.4, 'lot': 275, 'step': 50.0},
    "NAM-INDIA": {'spot': 1214.1, 'lot': 625, 'step': 20.0},
    "NATIONALUM": {'spot': 336.05, 'lot': 1875, 'step': 5.0},
    "NAUKRI": {'spot': 1035.35, 'lot': 550, 'step': 10.0},
    "NBCC": {'spot': 103.79, 'lot': 6500, 'step': 1.0},
    "NESTLEIND": {'spot': 1452.7, 'lot': 500, 'step': 10.0},
    "NHPC": {'spot': 78.9, 'lot': 6950, 'step': 1.0},
    "NIFTY": {'spot': 24354.0, 'lot': 65, 'step': 50.0},
    "NIFTYNXT50": {'spot': 72824.6, 'lot': 25, 'step': 100.0},
    "NMDC": {'spot': 86.1, 'lot': 6750, 'step': 1.0},
    "NTPC": {'spot': 359.4, 'lot': 1500, 'step': 5.0},
    "NUVAMA": {'spot': 1800.0, 'lot': 500, 'step': 20.0},
    "NYKAA": {'spot': 315.25, 'lot': 3125, 'step': 2.5},
    "OBEROIRLTY": {'spot': 1861.7, 'lot': 350, 'step': 20.0},
    "OFSS": {'spot': 11020.0, 'lot': 100, 'step': 100.0},
    "OIL": {'spot': 422.65, 'lot': 1400, 'step': 5.0},
    "ONGC": {'spot': 237.37, 'lot': 2250, 'step': 2.5},
    "PAGEIND": {'spot': 43025.0, 'lot': 20, 'step': 250.0},
    "PATANJALI": {'spot': 417.15, 'lot': 1075, 'step': 5.0},
    "PAYTM": {'spot': 1226.6, 'lot': 725, 'step': 10.0},
    "PERSISTENT": {'spot': 4541.9, 'lot': 125, 'step': 50.0},
    "PETRONET": {'spot': 278.7, 'lot': 1900, 'step': 5.0},
    "PFC": {'spot': 429.4, 'lot': 1300, 'step': 5.0},
    "PGEL": {'spot': 564.4, 'lot': 950, 'step': 10.0},
    "PHOENIXLTD": {'spot': 2029.8, 'lot': 350, 'step': 20.0},
    "PIDILITIND": {'spot': 1607.6, 'lot': 500, 'step': 10.0},
    "PIIND": {'spot': 2605.8, 'lot': 175, 'step': 20.0},
    "PNB": {'spot': 108.09, 'lot': 8000, 'step': 1.0},
    "PNBHOUSING": {'spot': 1061.0, 'lot': 650, 'step': 10.0},
    "POLICYBZR": {'spot': 1682.6, 'lot': 350, 'step': 20.0},
    "POLYCAB": {'spot': 9591.5, 'lot': 125, 'step': 100.0},
    "POWERGRID": {'spot': 289.3, 'lot': 1900, 'step': 2.5},
    "POWERINDIA": {'spot': 34000.0, 'lot': 25, 'step': 500.0},
    "PREMIERENE": {'spot': 1055.0, 'lot': 650, 'step': 10.0},
    "PRESTIGE": {'spot': 1681.0, 'lot': 450, 'step': 20.0},
    "RADICO": {'spot': 3988.6, 'lot': 150, 'step': 50.0},
    "RBLBANK": {'spot': 359.45, 'lot': 3175, 'step': 5.0},
    "RECLTD": {'spot': 369.05, 'lot': 1575, 'step': 5.0},
    "RELIANCE": {'spot': 1316.8, 'lot': 500, 'step': 10.0},
    "RVNL": {'spot': 236.52, 'lot': 1925, 'step': 5.0},
    "SAIL": {'spot': 169.8, 'lot': 4700, 'step': 2.5},
    "SBICARD": {'spot': 600.0, 'lot': 800, 'step': 10.0},
    "SBILIFE": {'spot': 1804.3, 'lot': 375, 'step': 20.0},
    "SBIN": {'spot': 1059.9, 'lot': 750, 'step': 10.0},
    "SHREECEM": {'spot': 26160.0, 'lot': 25, 'step': 250.0},
    "SHRIRAMFIN": {'spot': 1070.4, 'lot': 825, 'step': 10.0},
    "SIEMENS": {'spot': 3561.7, 'lot': 175, 'step': 50.0},
    "SOLARINDS": {'spot': 18794.0, 'lot': 50, 'step': 250.0},
    "SONACOMS": {'spot': 669.3, 'lot': 1225, 'step': 10.0},
    "SRF": {'spot': 2811.2, 'lot': 200, 'step': 20.0},
    "SUNPHARMA": {'spot': 1885.9, 'lot': 350, 'step': 20.0},
    "SUPREMEIND": {'spot': 3304.2, 'lot': 175, 'step': 50.0},
    "SUZLON": {'spot': 58.18, 'lot': 12700, 'step': 1.0},
    "SWIGGY": {'spot': 251.83, 'lot': 1825, 'step': 5.0},
    "TATACONSUM": {'spot': 1116.6, 'lot': 550, 'step': 10.0},
    "TATAELXSI": {'spot': 3595.5, 'lot': 125, 'step': 50.0},
    "TATAPOWER": {'spot': 380.65, 'lot': 1450, 'step': 5.0},
    "TATASTEEL": {'spot': 188.93, 'lot': 2750, 'step': 2.5},
    "TCS": {'spot': 2060.5, 'lot': 225, 'step': 20.0},
    "TECHM": {'spot': 1370.6, 'lot': 600, 'step': 20.0},
    "TIINDIA": {'spot': 3103.1, 'lot': 200, 'step': 20.0},
    "TITAN": {'spot': 4514.4, 'lot': 175, 'step': 50.0},
    "TMPV": {'spot': 349.75, 'lot': 1600, 'step': 5.0},
    "TORNTPHARM": {'spot': 4700.6, 'lot': 125, 'step': 50.0},
    "TRENT": {'spot': 3314.3, 'lot': 225, 'step': 20.0},
    "TVSMOTOR": {'spot': 3658.7, 'lot': 175, 'step': 20.0},
    "ULTRACEMCO": {'spot': 11668.0, 'lot': 50, 'step': 100.0},
    "UNIONBANK": {'spot': 170.65, 'lot': 4425, 'step': 2.5},
    "UNITDSPR": {'spot': 1375.2, 'lot': 400, 'step': 10.0},
    "UNOMINDA": {'spot': 1131.3, 'lot': 550, 'step': 20.0},
    "UPL": {'spot': 587.35, 'lot': 1355, 'step': 5.0},
    "VBL": {'spot': 514.95, 'lot': 1275, 'step': 5.0},
    "VEDL": {'spot': 277.95, 'lot': 1150, 'step': 5.0},
    "VMM": {'spot': 122.56, 'lot': 4850, 'step': 2.5},
    "VOLTAS": {'spot': 1296.1, 'lot': 375, 'step': 20.0},
    "WAAREEENER": {'spot': 2888.0, 'lot': 175, 'step': 50.0},
    "WIPRO": {'spot': 169.1, 'lot': 3000, 'step': 2.5},
    "YESBANK": {'spot': 24.55, 'lot': 31100, 'step': 1.0},
    "ZYDUSLIFE": {'spot': 1111.6, 'lot': 900, 'step': 10.0},
}

# ─── FUNCTIONS ────────────────────────────────────────────────────────────────

def _generate_mock_strikes(spot: float, step: int, num_strikes: int, base_iv: float) -> list:
    strikes = []
    half = num_strikes // 2
    start = (int(spot) // step) * step - (half * step)
    for i in range(num_strikes):
        strike = start + (i * step)
        dist = strike - spot
        strike_iv = base_iv + (abs(dist) / spot) * 0.8
        atm_price = spot * 0.0092

        intrinsic_call = max(0.0, spot - strike)
        tv_call = atm_price * math.exp(-abs(dist) / (step * 3))
        call_ltp = round(intrinsic_call + tv_call, 2)

        intrinsic_put = max(0.0, strike - spot)
        tv_put = atm_price * math.exp(-abs(dist) / (step * 3))
        put_ltp = round(intrinsic_put + tv_put, 2)

        spread_mult = 1 + (abs(dist) / (step * 10))
        call_delta = max(0.01, min(0.99, 0.5 - (dist / (step * 10))))
        put_delta = call_delta - 1.0
        oi_mult = max(0.1, 1.0 - (abs(dist) / (step * 5)))
        base_oi = 150000 if i % 5 == 0 else 50000

        strikes.append({
            "strike": float(strike),
            "call": {
                "ltp": call_ltp,
                "bid": round(call_ltp * 0.98, 2),
                "ask": round(call_ltp * 1.02 + (1.5 * spread_mult), 2),
                "oi": int(base_oi * oi_mult),
                "volume": int(base_oi * oi_mult * 1.5),
                "iv": round(strike_iv, 4),
                "delta": round(call_delta, 2),
                "theta": -15.5,
                "gamma": 0.002,
                "vega": 12.0
            },
            "put": {
                "ltp": put_ltp,
                "bid": round(put_ltp * 0.98, 2),
                "ask": round(put_ltp * 1.02 + (1.5 * spread_mult), 2),
                "oi": int(base_oi * oi_mult * 0.9),
                "volume": int(base_oi * oi_mult * 1.4),
                "iv": round(strike_iv, 4),
                "delta": round(put_delta, 2),
                "theta": -14.2,
                "gamma": 0.002,
                "vega": 12.0
            }
        })
    return strikes

def get_option_chain(symbol: str) -> dict:
    sym = symbol.upper()
    if sym in asset_config:
        cfg = asset_config[sym]
        spot = cfg["spot"]
        lot_size = cfg["lot"]
        step = cfg["step"]
        current_iv = 0.15
    else:
        # Fallback to NIFTY data (from the same dict)
        nifty = asset_config["NIFTY"]
        spot = nifty["spot"]
        lot_size = nifty["lot"]
        step = nifty["step"]
        current_iv = 0.138
        sym = "NIFTY"

    atm_straddle = spot * 0.018
    expiry = (datetime.utcnow() + timedelta(days=24)).strftime("%Y-%m-%d")

    return {
        "symbol": sym,
        "spot": spot,
        "timestamp": datetime.utcnow().isoformat(),
        "expiry": expiry,
        "days_to_expiry": 24,
        "iv_rank": 42.0,
        "current_iv": current_iv,
        "iv_52w_high": 0.28,
        "iv_52w_low": 0.09,
        "atm_straddle_price": atm_straddle,
        "lot_size": lot_size,
        "strikes": _generate_mock_strikes(spot, step, 21, current_iv)
    }