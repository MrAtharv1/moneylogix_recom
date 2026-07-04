from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import logging
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv
from huggingface_hub import AsyncInferenceClient
from data.mock_data import asset_config

load_dotenv()
router = APIRouter()
logger = logging.getLogger(__name__)

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
    target = today + timedelta(days=days_ahead)
    return target.strftime("%Y-%m-%d")

def _build_leg(symbol: str, strike: float, expiry: str, option_type: str, side: str,
               quantity: int, iv: float, lot_size: int) -> dict:
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
async def prompt_to_trade(request: PromptRequest):
    from config import settings

    if settings.AI_PROVIDER != "huggingface":
        logger.warning("AI_PROVIDER is not 'huggingface'. Falling back to mock generation.")
        return _generate_fallback_strategy(request.text)

    hf_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_token:
        logger.error("HUGGINGFACE_API_KEY missing")
        return _generate_fallback_strategy(request.text, error="API key missing")

    try:
        # ASYNC CLIENT
        client = AsyncInferenceClient(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            token=hf_token
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.text}
        ]
        
        # AWAIT GENERATION
        response = await client.chat_completion(
            messages=messages,
            max_tokens=500,
            temperature=0.1
        )
        raw_text = response.choices[0].message.content.strip()
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("No JSON found in LLM response")
        clean = raw_text[start:end+1]
        data = json.loads(clean)

        if not data.get("success"):
            return data

        symbol = str(data.get("symbol", "NIFTY")).upper()
        timeframe = data.get("timeframe", "this_week")
        budget = float(data.get("budget", 10000))
        expiry_date = get_next_thursday(timeframe)

        # Dynamic fallback hackathon check
        if symbol in asset_config:
            spot_price = asset_config[symbol]["spot"]
            lot_size = asset_config[symbol]["lot"]
            strike_step = asset_config[symbol]["step"]
        else:
            nifty = asset_config["NIFTY"]
            spot_price, lot_size, strike_step = nifty["spot"], nifty["lot"], nifty["step"]
            symbol = "NIFTY"

        margin_per_lot = 25000 
        calculated_qty = max(1, min(50, int(budget // margin_per_lot)))
        strategy = data.get("requested_strategy", "")
        final_legs = []

        if data.get("legs") and len(data["legs"]) > 0:
            for leg in data["legs"]:
                final_legs.append(_build_leg(symbol, leg.get("strike", spot_price), leg.get("expiry", expiry_date), leg.get("option_type", "Call"), leg.get("side", "Buy"), leg.get("quantity", calculated_qty), leg.get("iv", 13.8), lot_size))
        else:
            st = strategy.lower()
            if "condor" in st or "iron" in st:
                final_legs = [
                    _build_leg(symbol, spot_price - strike_step*2, expiry_date, "Put", "Buy", calculated_qty, 13.5, lot_size),
                    _build_leg(symbol, spot_price - strike_step, expiry_date, "Put", "Sell", calculated_qty, 13.6, lot_size),
                    _build_leg(symbol, spot_price + strike_step, expiry_date, "Call", "Sell", calculated_qty, 13.7, lot_size),
                    _build_leg(symbol, spot_price + strike_step*2, expiry_date, "Call", "Buy", calculated_qty, 13.8, lot_size),
                ]
            elif "straddle" in st:
                final_legs = [
                    _build_leg(symbol, spot_price, expiry_date, "Call", "Buy", calculated_qty, 13.8, lot_size),
                    _build_leg(symbol, spot_price, expiry_date, "Put", "Buy", calculated_qty, 13.8, lot_size),
                ]
            elif "strangle" in st:
                final_legs = [
                    _build_leg(symbol, spot_price - strike_step, expiry_date, "Put", "Buy", calculated_qty, 13.8, lot_size),
                    _build_leg(symbol, spot_price + strike_step, expiry_date, "Call", "Buy", calculated_qty, 13.8, lot_size),
                ]
            elif "bear" in st and "put" in st:
                final_legs = [
                    _build_leg(symbol, spot_price, expiry_date, "Put", "Buy", calculated_qty, 13.8, lot_size),
                    _build_leg(symbol, spot_price - strike_step, expiry_date, "Put", "Sell", calculated_qty, 13.9, lot_size),
                ]
            elif "bull" in st and "put" in st:
                final_legs = [
                    _build_leg(symbol, spot_price - strike_step, expiry_date, "Put", "Sell", calculated_qty, 13.6, lot_size),
                    _build_leg(symbol, spot_price - strike_step*2, expiry_date, "Put", "Buy", calculated_qty, 13.5, lot_size),
                ]
            elif "covered call" in st:
                final_legs = [_build_leg(symbol, spot_price + strike_step, expiry_date, "Call", "Sell", calculated_qty, 13.7, lot_size)]
            else:
                final_legs = [
                    _build_leg(symbol, spot_price, expiry_date, "Call", "Buy", calculated_qty, 13.8, lot_size),
                    _build_leg(symbol, spot_price + strike_step, expiry_date, "Call", "Sell", calculated_qty, 13.9, lot_size),
                ]

        return {
            "success": True,
            "message": f"Loaded {strategy or 'custom'} for {symbol} (Qty: {calculated_qty} lots).",
            "requested_strategy": strategy,
            "symbol": symbol,
            "legs": final_legs
        }

    except Exception as e:
        logger.exception(f"AI router error: {e}")
        return _generate_fallback_strategy(request.text, error=str(e))

def _generate_fallback_strategy(text: str, error: str = None) -> dict:
    logger.info("Generating fallback strategy for: %s", text[:50])
    expiry = get_next_thursday("this_week")
    nifty = asset_config.get("NIFTY", {"spot": 24354.0, "lot": 65, "step": 50})
    spot, lot, step = nifty["spot"], nifty["lot"], nifty["step"]
    return {
        "success": True,
        "message": f"Fallback strategy loaded (AI unavailable: {error or 'internal error'})",
        "symbol": "NIFTY",
        "legs": [
            _build_leg("NIFTY", spot - step*2, expiry, "Put", "Buy", 1, 13.5, lot),
            _build_leg("NIFTY", spot - step, expiry, "Put", "Sell", 1, 13.6, lot),
            _build_leg("NIFTY", spot + step, expiry, "Call", "Sell", 1, 13.7, lot),
            _build_leg("NIFTY", spot + step*2, expiry, "Call", "Buy", 1, 13.8, lot),
        ]
    }