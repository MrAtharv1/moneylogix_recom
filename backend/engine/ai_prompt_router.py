from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()
router = APIRouter()

class PromptRequest(BaseModel):
    text: str

SYSTEM_PROMPT = """You are a strict algorithmic extraction API. Your ONLY job is to analyze natural language and map it to a highly structured JSON options trading blueprint.
You MUST output RAW JSON ONLY. Absolutely NO conversational text, NO pleasantries, NO explanations, and NO markdown formatting (do NOT wrap in ```json).

### EXTRACTION TARGETS & FALLBACKS
1. "symbol": The specific stock or index mentioned (e.g., "Reliance" -> "RELIANCE", "Airtel" -> "BHARTIARTL", "BankNifty" -> "BANKNIFTY"). Default to "NIFTY" ONLY if no asset is explicitly mentioned.
2. "budget": The exact numeric capital the user states. Default to 10000 ONLY if no money/capital is mentioned.
3. "intent": The user's market view. Map to "bullish" (up/rise), "bearish" (down/fall), or "neutral" (sideways/flat).
4. "timeframe": Map to "this_week", "next_week", or "next_month". Default to "this_week".
5. "requested_strategy": The exact strategy named (e.g., "Straddle", "Iron Condor"). IF NOT NAMED, infer it ONLY from intent: "bullish" = "Bull Call Spread", "bearish" = "Bear Put Spread", "neutral" = "Iron Condor".
6. "legs": ONLY populate if the user dictates EXACT strike prices, exact Call/Put types, and Buy/Sell sides (e.g., "buy 19000 call"). Otherwise, leave as an empty array [].

### STRICT BUSINESS LOGIC (THE RULES)
- RULE 1 (EXPLICIT PRIORITY): You must prioritize the exact variables the user provides. Only use calculated defaults or inferred strategies if the user completely omits that specific detail.
- RULE 2 (THE FAILURE CONDITION): If the user does not name an explicit strategy, AND you cannot extract their market direction (intent), you MUST fail. Set "success": false and "message": "I need a bit more context. Please clarify your market view (e.g., bullish, bearish) and your budget."
- RULE 3 (NO LAZINESS): Scan the entire text. Look for hidden contextual clues for budget (rs, rupees, k, capital) and assets.

### JSON SCHEMA FORMAT
Your output MUST exactly match this structure and data types:
{
  "success": true | false,
  "message": "empty if success, error reason if false",
  "requested_strategy": "string",
  "intent": "string",
  "symbol": "string",
  "timeframe": "string",
  "budget": 10000,
  "legs": []
}"""

def get_next_thursday(timeframe: str) -> str:
    today = datetime.today()
    days_ahead = (3 - today.weekday()) % 7
    if days_ahead == 0 and timeframe == "this_week":
        days_ahead = 0
    if timeframe == "next_week":
        days_ahead += 7
    elif timeframe == "next_month":
        days_ahead += 28 
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime("%Y-%m-%d")

def _build_leg(symbol: str, strike: float, expiry: str, option_type: str, side: str, quantity: int, iv: float, lot_size: int) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "strike": float(strike),
        "expiry": expiry,
        "option_type": option_type.lower(),
        "side": side.lower(),
        "quantity": max(1, int(quantity)),
        "lot_size": int(lot_size),
        "iv": float(iv) / 100.0 if float(iv) > 1 else float(iv), 
    }

@router.post("/api/prompt-to-trade")
def prompt_to_trade(request: PromptRequest):
    hf_token = os.getenv("HUGGINGFACE_API_KEY")

    if not hf_token:
        raise HTTPException(status_code=500, detail="Hugging Face API token missing.")
    
    client = InferenceClient(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        token=hf_token
    )
    
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.text}
        ]
        
        response = client.chat_completion(
            messages=messages,
            max_tokens=500,
            temperature=0.1
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found in LLM response.")
            
        clean_json_str = raw_text[start_idx:end_idx+1]
        data = json.loads(clean_json_str)
        
        if not data.get("success"):
            return data

        # AI extracts the symbol. If it fails, default to NIFTY.
        symbol = str(data.get("symbol", "NIFTY")).upper()
        timeframe = data.get("timeframe", "this_week")
        budget = float(data.get("budget", 10000))
        expiry_date = get_next_thursday(timeframe)
        
        # --- NEW: DYNAMIC ASSET DICTIONARY ---
        # We define the core metrics for common stocks here. 
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
        

        # If the symbol is in our dictionary, use exact NSE metrics.
        if symbol in asset_config:
            spot_price = asset_config[symbol]["spot"]
            lot_size = asset_config[symbol]["lot"]
            strike_step = asset_config[symbol]["step"]
        else:
            # CRITICAL FIX: If the stock isn't in the dictionary, DO NOT overwrite the symbol!
            # Just provide a generic, safe fallback for the math to render.
            spot_price = 1000.0
            lot_size = 100
            strike_step = 10
            
        # --- DYNAMIC BUDGET SIZING ---
        margin_per_lot = 25000
        calculated_quantity = int(budget // margin_per_lot)
        if calculated_quantity < 1:
            calculated_quantity = 1
        
        final_legs = []
        strategy = data.get("requested_strategy", "")
        
        # --- DYNAMIC RECIPE BUILDER ---
        if not data.get("legs") or len(data["legs"]) == 0:
            if "Condor" in str(strategy):
                final_legs = [
                    _build_leg(symbol, spot_price - (strike_step * 2), expiry_date, "Put", "Buy", calculated_quantity, 13.5, lot_size),
                    _build_leg(symbol, spot_price - strike_step, expiry_date, "Put", "Sell", calculated_quantity, 13.6, lot_size),
                    _build_leg(symbol, spot_price + strike_step, expiry_date, "Call", "Sell", calculated_quantity, 13.7, lot_size),
                    _build_leg(symbol, spot_price + (strike_step * 2), expiry_date, "Call", "Buy", calculated_quantity, 13.8, lot_size),
                ]
            elif "Bear" in str(strategy):
                final_legs = [
                    _build_leg(symbol, spot_price, expiry_date, "Put", "Buy", calculated_quantity, 13.8, lot_size),
                    _build_leg(symbol, spot_price - strike_step, expiry_date, "Put", "Sell", calculated_quantity, 13.9, lot_size),
                ]
            else:  # Default to Bull Call Spread
                final_legs = [
                    _build_leg(symbol, spot_price, expiry_date, "Call", "Buy", calculated_quantity, 13.8, lot_size),
                    _build_leg(symbol, spot_price + strike_step, expiry_date, "Call", "Sell", calculated_quantity, 13.9, lot_size),
                ]
        else:
            for leg in data["legs"]:
                final_legs.append(
                    _build_leg(
                        symbol=symbol,
                        strike=leg.get("strike", spot_price),
                        expiry=leg.get("expiry", expiry_date),
                        option_type=leg.get("option_type", "Call"),
                        side=leg.get("side", "Buy"),
                        quantity=leg.get("quantity", calculated_quantity),
                        iv=leg.get("iv", 13.8),
                        lot_size=lot_size
                    )
                )
                
        return {
            "success": True,
            "message": f"Successfully loaded {strategy or 'custom strategy'} for {symbol} (Qty: {calculated_quantity} lots).",
            "requested_strategy": strategy,
            "symbol": symbol,
            "legs": final_legs
        }
        
    except Exception as e:
        print(f"\n❌ BACKEND AI CRASH: {str(e)}\n")
        fallback_expiry = get_next_thursday("this_week")
        return {
            "success": True,
            "message": "Unable to extract context. Loading fallback Iron Condor.",
            "symbol": "NIFTY",
            "legs": [
                _build_leg("NIFTY", 18800, fallback_expiry, "Put", "Buy", 1, 13.5, 50),
                _build_leg("NIFTY", 18900, fallback_expiry, "Put", "Sell", 1, 13.6, 50),
                _build_leg("NIFTY", 19100, fallback_expiry, "Call", "Sell", 1, 13.7, 50),
                _build_leg("NIFTY", 19200, fallback_expiry, "Call", "Buy", 1, 13.8, 50),
            ]
        }