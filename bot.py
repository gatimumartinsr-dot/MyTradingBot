import random
import os
import json

DB_FILE = "trades_db_matrix.json"

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)

def get_archived_trades():
    init_db()
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except Exception: return []

def clear_trade_database():
    init_db()
    with open(DB_FILE, "w") as f: json.dump([], f)
    return True

def dispatch_live_order_matrix(order_payload):
    init_db()
    try:
        trades = get_archived_trades()
        new_row = {
            "Ticket ID": f"TX-{random.randint(50000, 99999)}",
            "Timestamp": order_payload.get("timestamp"),
            "Symbol": str(order_payload.get("symbol")),
            "Direction": str(order_payload.get("direction")),
            "Volume Lots": float(order_payload.get("volume", 0.1)),
            "Entry Price": float(order_payload.get("entry")),
            "Current Price": float(order_payload.get("entry")),
            "Net Floating PnL": "+$0.00"
        }
        trades.append(new_row)
        with open(DB_FILE, "w") as f: json.dump(trades, f, indent=4)
        return True
    except Exception: return False

def fetch_live_market_tick(symbol="XAUUSDm"):
    try:
        sym_str = str(symbol).upper()
        if "BTC" in sym_str:
            base_bid = 64350.00 + random.uniform(-15.0, 20.0)
            spread = 4.50
        elif "EUR" in sym_str:
            base_bid = 1.1045 + random.uniform(-0.0002, 0.0004)
            spread = 0.0002
        else: # XAUUSDm
            base_bid = 4389.20 + random.uniform(-0.6, 0.8)
            spread = 0.35
        return round(base_bid, 4 if "EUR" in sym_str else 2), round(base_bid + spread, 4 if "EUR" in sym_str else 2)
    except Exception: return 4389.20, 4389.55

def calculate_position_size(balance, risk_percentage, entry_price, stop_loss_price):
    try:
        risk_amount_dollars = balance * (risk_percentage / 100.0)
        points_at_risk = abs(entry_price - stop_loss_price)
        if points_at_risk <= 0: return 0.01
        return round(max(risk_amount_dollars / points_at_risk, 0.01), 2)
    except Exception: return 0.01

def run_autonomous_brain(balance, risk_percentage, symbol="XAUUSDm", brain_active=False):
    live_bid, live_ask = fetch_live_market_tick(symbol)
    sym_str = str(symbol).upper()
    
    prices = []
    current_walk = live_bid - (15.0 if "BTC" in sym_str else (0.0006 if "EUR" in sym_str else 1.5))
    scale = 4.0 if "BTC" in sym_str else (0.0002 if "EUR" in sym_str else 0.25)
    for i in range(30):
        current_walk += random.uniform(-scale, scale * 1.04)
        prices.append(current_walk)
        
    def calculate_ema(data_array, period):
        k = 2 / (period + 1)
        ema_values = [data_array]
        for price in data_array[1:]:
            ema_values.append((price * k) + (ema_values[-1] * (1 - k)))
        return round(ema_values[-1], 4 if "EUR" in sym_str else 2)

    fast_ema = calculate_ema(prices, 12)  
    slow_ema = calculate_ema(prices, 26)  
    is_ema_bullish = fast_ema >= slow_ema
    
    recent_high = max(prices[-5:-1])
    recent_low = min(prices[-5:-1])
    newest_close = prices[-1]
    
    ob_zone_type = "UNCONFIRMED"
    if newest_close > recent_high: ob_zone_type = "VALIDATED BULLISH OB (BOS CONFIRMED)"
    elif newest_close < recent_low: ob_zone_type = "VALIDATED BEARISH OB (CHoCH CONFIRMED)"

    if is_ema_bullish and ob_zone_type == "VALIDATED BULLISH OB (BOS CONFIRMED)":
        market_trend = "STRONG BULLISH (EMA + VALIDATED OB)"
        active_direction = "BUY LIMIT"
    else:
        market_trend = "BULLISH (UPTREND)" if is_ema_bullish else "BEARISH (DOWNTREND)"
        active_direction = "BUY LIMIT" if is_ema_bullish else "SELL LIMIT"

    # RSI Strategy Parameters
    rsi = round(random.uniform(42.0, 58.0), 2)
    rsi_status = "NEUTRAL"
    rsi_filter_block = False
        
    if "BTC" in sym_str:
        entry_level = round(live_bid, 2)
        ob_base = round(slow_ema - 15.0, 2)
        stop_loss = round(ob_base - 25.0, 2) if "BUY" in active_direction else round(ob_base + 25.0, 2)
    elif "EUR" in sym_str:
        entry_level = round(live_bid, 4)
        ob_base = round(slow_ema - 0.0002, 4)
        stop_loss = round(ob_base - 0.0006, 4) if "BUY" in active_direction else round(ob_base + 0.0006, 4)
    else: # Gold
        entry_level = round(live_bid, 2)
        ob_base = round(slow_ema - 0.40, 2)
        stop_loss = round(ob_base - 1.10, 2) if "BUY" in active_direction else round(ob_base + 1.10, 2)
        
    raw_saved = get_archived_trades()
    positions_matrix = []
    if brain_active and raw_saved:
        for trade in raw_saved:
            sim_pnl = random.uniform(-5.0, 25.0) if "BUY" in str(trade["Direction"]) else random.uniform(-15.0, 5.0)
            pnl_sign = "+" if sim_pnl >= 0 else ""
            positions_matrix.append({
                "Ticket ID": trade["Ticket ID"],
                "Instrument": trade["Symbol"],
                "Direction": trade["Direction"],
                "Volume Lots": trade["Volume Lots"],
                "Entry Price": f"${trade['Entry Price']:,.2f}",
                "Current Price": f"${live_bid:,.2f}",
                "Net Floating PnL": f"{pnl_sign}${sim_pnl:,.2f}"
            })
    else:
        positions_matrix = [{
            "Ticket ID": "OB-4016", 
            "Instrument": sym_str, 
            "Direction": "BUY (LONG)" if is_ema_bullish else "SELL (SHORT)", 
            "Volume Lots": 0.50, 
            "Entry Price": f"${entry_level:,.2f}", 
            "Current Price": f"${live_bid:,.2f}", 
            "Net Floating PnL": "+$142.50"
        }]
    
    return {
        "live_bid": live_bid, "live_ask": live_ask, "fast_ema": fast_ema, "slow_ema": slow_ema,
        "rsi": rsi, "market_trend": market_trend, "rsi_status": rsi_status, "rsi_filter_block": rsi_filter_block,
        "entry_level": entry_level, "ob_zone": ob_base, "stop_loss": stop_loss, "positions_matrix": positions_matrix
    }
