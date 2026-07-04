"""payoff.py — Strategy P&L at expiry across a range of underlying prices."""
import logging
logger = logging.getLogger(__name__)
DIRECTION_SIGN = {"buy": 1, "sell": -1}

def _intrinsic_value(option_type: str, strike: float, underlying_price: float) -> float:
    opt = option_type.strip().lower()
    if opt == "call":
        return max(0.0, underlying_price - strike)
    elif opt == "put":
        return max(0.0, strike - underlying_price)
    raise ValueError(f"Unknown option_type '{option_type}'")

def compute_payoff_curve(legs: list[dict], spot: float, num_points: int = 100) -> list[dict]:
    if not legs:
        return []
    if spot <= 0:
        raise ValueError(f"Invalid spot price: {spot}")
        
    lower = spot * 0.90
    upper = spot * 1.10
    step = (upper - lower) / (num_points - 1) if num_points > 1 else 0
    prices = [lower + i * step for i in range(num_points)]
    
    curve = []
    for price in prices:
        total = 0.0
        for leg in legs:
            strike = float(leg["strike"])
            opt = leg["option_type"]
            side = leg.get("side", "buy").lower()
            qty = int(leg.get("quantity", 1))
            lot = int(leg.get("lot_size", 50))
            entry = float(leg.get("entry_price", 0.0))
            
            if side not in DIRECTION_SIGN:
                continue
                
            intrinsic = _intrinsic_value(opt, strike, price)
            total += (intrinsic - entry) * qty * lot * DIRECTION_SIGN[side]
            
        curve.append({"price": round(price, 2), "pnl": round(total, 2)})
    return curve

def find_breakevens(curve: list[dict]) -> list[float]:
    if len(curve) < 2:
        return []
    b = []
    for i in range(len(curve) - 1):
        pnl1 = curve[i]["pnl"]
        pnl2 = curve[i+1]["pnl"]
        p1 = curve[i]["price"]
        p2 = curve[i+1]["price"]
        if pnl1 * pnl2 < 0:
            denom = pnl2 - pnl1
            if abs(denom) < 1e-10:
                continue
            b.append(round(p1 + (-pnl1) * (p2 - p1) / denom, 2))
        elif pnl1 == 0.0:
            b.append(round(p1, 2))
    return sorted(b)

def compute_max_profit_loss(curve: list[dict], legs: list[dict] = None) -> dict:
    UNLIMITED_PROFIT = 999999999.0
    UNLIMITED_LOSS = -999999999.0
    
    if not curve:
        return {"max_profit": 0.0, "max_loss": 0.0}
        
    pnls = [p["pnl"] for p in curve]
    best = max(pnls)
    worst = min(pnls)

    if not legs:
        # Fallback to standard min/max if legs are not provided
        return {"max_profit": round(best, 2), "max_loss": round(worst, 2)}

    # Analytic Boundary Check
    # Calculate the net directional position at extreme bounds
    net_calls = 0.0
    net_puts = 0.0
    
    for leg in legs:
        side = leg.get("side", "buy").lower()
        opt = leg.get("option_type", "call").lower()
        qty = int(leg.get("quantity", 1))
        lot = int(leg.get("lot_size", 50))
        
        dir_mult = 1 if side == "buy" else -1
        exposure = qty * lot * dir_mult
        
        if opt == "call":
            net_calls += exposure
        elif opt == "put":
            net_puts += exposure

    unlimited_profit = False
    unlimited_loss = False

    # As spot -> Infinity, PnL is driven entirely by net_calls
    if net_calls > 0:
        unlimited_profit = True
    elif net_calls < 0:
        unlimited_loss = True
        
    # As spot -> 0, PnL is driven entirely by net_puts
    # A long put profits as price drops (profit). A short put loses as price drops (loss).
    if net_puts > 0:
        unlimited_profit = True
    elif net_puts < 0:
        unlimited_loss = True

    mp = UNLIMITED_PROFIT if unlimited_profit else round(best, 2)
    ml = UNLIMITED_LOSS if unlimited_loss else round(worst, 2)
    
    return {"max_profit": mp, "max_loss": ml}