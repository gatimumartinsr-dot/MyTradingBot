import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import urllib.request
import json

def initialize_mt5(login=None, password=None, server=None):
    if not mt5.initialize():
        return False
    if login and password and server:
        return mt5.login(login=int(login), password=password, server=server)
    return True

def is_within_dubai_window(window_type="Power Hour"):
    dubai_tz = pytz.timezone('Asia/Dubai')
    now_dubai = datetime.now(dubai_tz).time()
    london_start = datetime.strptime("11:00:00", "%H:%M:%S").time()
    london_end = datetime.strptime("13:00:00", "%H:%M:%S").time()
    power_start = datetime.strptime("16:00:00", "%H:%M:%S").time()
    power_end = datetime.strptime("18:00:00", "%H:%M:%S").time()
    if window_type == "London Breakout":
        return london_start <= now_dubai <= london_end
    elif window_type == "Power Hour":
        return power_start <= now_dubai <= power_end
    return False

def calculate_position_size(balance, risk_pct, stop_loss_pips, symbol):
    risk_amount = balance * (risk_pct / 100)
    if "XAU" in symbol:
        lot_size = risk_amount / (stop_loss_pips * 2.0)
    elif "XAG" in symbol:
        lot_size = risk_amount / (stop_loss_pips * 5.0)
    else:
        pip_value = 10.0 if "USD" in symbol else 1.0
        lot_size = risk_amount / (stop_loss_pips * pip_value)
    return max(0.01, round(lot_size, 2))

def send_limit_order(symbol, order_type, entry_price, stop_loss, take_profit, lot_size):
    mt5_order_type = mt5.ORDER_TYPE_BUY_LIMIT if order_type == "BUY_LIMIT" else mt5.ORDER_TYPE_SELL_LIMIT
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(lot_size),
        "type": mt5_order_type,
        "price": float(entry_price),
        "sl": 0.0, 
        "tp": 0.0,
        "deviation": 30,
        "magic": 202609,
        "comment": "Claude Ultimate Framework",
        "type_time": mt5.ORDER_TIME_DAY,
        "type_filling": mt5.ORDER_FILLING_RETURN, 
    }
    result = mt5.order_send(request)
    if result is not None and result.retcode == 10013:
        request["type_filling"] = mt5.ORDER_FILLING_IOC
        result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        err_code = result.retcode if result else "Terminal Missing"
        return {"status": "FAILED", "message": f"Server Rejected Order parameters. Error: {err_code}."}
    
    order_ticket = result.order
    modify_request = {
        "action": mt5.TRADE_ACTION_MODIFY,
        "order": order_ticket,
        "price": float(entry_price),
        "sl": float(stop_loss),
        "tp": float(take_profit),
        "type_time": mt5.ORDER_TIME_DAY
    }
    mt5.order_send(modify_request)
    return {"status": "SUCCESS", "order_id": order_ticket}

def fetch_economic_news():
    """Fetches high-impact financial calendar events live for USD and major currency groups."""
    try:
        url = "https://financialmodelingprep.com"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            # Filter specifically for high-impact market drivers matching today's timeline
            today_str = datetime.today().strftime('%Y-%m-%d')
            high_impact_events = [
                event for event in data 
                if event.get('date', '').startswith(today_str) and event.get('impact') == 'High' and event.get('currency') in ['USD', 'EUR', 'GBP']
            ]
            return high_impact_events
    except Exception:
        return []

def manage_active_trades_with_trailing(trail_pips=20.0):
    """
    Automates live position management:
    1. Triggers Breakeven adjustments at 1:1 risk-to-reward ratio milestones.
    2. Activates an active Trailing Stop-Loss protection layer to lock in running gains safely.
    """
    initialize_mt5()
    open_positions = mt5.positions_get(magic=202609)
    if not open_positions:
        return "No active managed positions found."

    trail_dist = trail_pips * 0.10 if "XAU" in open_positions[0].symbol else trail_pips * 0.0001
    count = 0

    for pos in open_positions:
        ticket = pos.ticket
        entry = pos.price_open
        current_price = pos.price_current
        sl = pos.sl
        symbol = pos.symbol
        
        risk_dist = abs(entry - sl)
        if risk_dist == 0:
            continue

        # Adjust trail steps dynamically if dealing with Gold metrics
        current_trail_dist = trail_pips * 0.10 if "XAU" in symbol else trail_pips * 0.0001

        if pos.type == mt5.POSITION_TYPE_BUY:
            # Step 1: Initial Breakeven Protection at 1:1 milestone
            if (current_price - entry) >= risk_dist and sl < entry:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": entry, "tp": pos.tp})
                sl = entry
            
            # Step 2: Trailing Stop-Loss activation loop
            if current_price - entry > current_trail_dist:
                new_sl = round(current_price - current_trail_dist, 5)
                if sl == 0.0 or new_sl > sl:
                    mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": pos.tp})
                    count += 1

        elif pos.type == mt5.POSITION_TYPE_SELL:
            # Step 1: Initial Breakeven Protection at 1:1 milestone
            if (entry - current_price) >= risk_dist and sl > entry:
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": entry, "tp": pos.tp})
                sl = entry
            
            # Step 2: Trailing Stop-Loss activation loop
            if entry - current_price > current_trail_dist:
                new_sl = round(current_price + current_trail_dist, 5)
                if sl == 0.0 or new_sl < sl:
                    mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": pos.tp})
                    count += 1
                    
    return f"Scan finished. Adjusted {count} active stop-loss levels to lock in profit."
