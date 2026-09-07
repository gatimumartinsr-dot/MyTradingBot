import random
import os
import json
from datetime import datetime

DB_FILE = "trades.json"
AUDIT_FILE = "audit_log.json"
NOTES_FILE = "session_notes.json"

def init_databases():
    """Initializes the persistent JSON trade tracking, audit logs, and notes storage containers."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump([], f)
    if not os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "w") as f: json.dump([], f)
    if not os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "w") as f: json.dump([], f)

def log_user_activity(operator, event_action, details):
    try:
        init_databases()
        with open(AUDIT_FILE, "r") as f: logs = json.load(f)
        new_log = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Operator Key": str(operator).upper(),
            "Action Parameter": str(event_action),
            "Operational Details": str(details)
        }
        logs.append(new_log)
        with open(AUDIT_FILE, "w") as f: json.dump(logs, f, indent=4)
        return True
    except Exception: return False

def get_audit_logs():
    try:
        init_databases()
        with open(AUDIT_FILE, "r") as f: return json.load(f)
    except Exception: return []

def clear_audit_ledger():
    try:
        with open(AUDIT_FILE, "w") as f: json.dump([], f)
        return True
    except Exception: return False

def store_manual_note(operator, note_text):
    try:
        init_databases()
        with open(NOTES_FILE, "r") as f: notes = json.load(f)
        new_note = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Author": str(operator).upper(),
            "Journal Note Entry": str(note_text)
        }
        notes.append(new_note)
        with open(NOTES_FILE, "w") as f: json.dump(notes, f, indent=4)
        return True
    except Exception: return False

def get_manual_notes():
    try:
        init_databases()
        with open(NOTES_FILE, "r") as f: json.load(f)
    except Exception: return []

def fetch_live_market_tick(symbol="XAUUSDm"):
    try:
        sym_str = str(symbol).upper()
        if "BTC" in sym_str:
            base_bid = 64350.00 + random.uniform(-25.0, 35.0)
            spread = round(random.uniform(2.50, 5.00), 2)
        elif "EUR" in sym_str:
            base_bid = 1.1045 + random.uniform(-0.0004, 0.0006)
            spread = 0.0002
        else:
            base_bid = 2514.11 + random.uniform(-0.5, 0.5)
            spread = 0.30
        return round(base_bid, 4), round(base_bid + spread, 4)
    except Exception: return 2514.11, 2514.41

def calculate_position_size(balance, risk_percentage, entry_price, stop_loss_price, multiplier=1.0):
    try:
        risk_amount_dollars = balance * (risk_percentage / 100.0)
        points_at_risk = abs(entry_price - stop_loss_price)
        if points_at_risk <= 0: return 0.01
        return round(max((risk_amount_dollars / points_at_risk) * float(multiplier), 0.01), 2)
    except Exception: return 0.01

def dispatch_live_order_matrix(order_payload):
    try:
        init_databases()
        with open(DB_FILE, "r") as f: trades = json.load(f)
        new_trade_entry = {
            "ID": f"TX-{random.randint(100000, 999999)}",
            "Timestamp": order_payload.get("timestamp"),
            "Symbol": order_payload.get("symbol"),
            "Action": order_payload.get("direction"),
            "Lots": float(order_payload.get("volume", 0.01)),
            "Entry": float(order_payload.get("entry")),
            "Stop Loss": float(order_payload.get("sl")),
            "Take Profit": float(order_payload.get("tp")),
            "Status": "PROCESSED_ROUTED"
        }
        trades.append(new_trade_entry)
        with open(DB_FILE, "w") as f: json.dump(trades, f, indent=4)
        return True
    except Exception: return False

def get_archived_trades():
    try:
        init_databases()
        with open(DB_FILE, "r") as f: return json.load(f)
    except Exception: return []

def clear_trade_database():
    try:
        with open(DB_FILE, "w") as f: json.dump([], f)
        return True
    except Exception: return False

def run_autonomous_brain(balance, risk_percentage, symbol="XAUUSDm"):
    sym_str = str(symbol).upper()
    live_bid, live_ask = fetch_live_market_tick(sym_str)
    
    if "BTC" in sym_str:
        fast_ema_sim = round(live_bid + random.uniform(-5.0, 12.0), 2)
        slow_ema_sim = 64350.00
    elif "EUR" in sym_str:
        fast_ema_sim = round(live_bid + random.uniform(-0.0002, 0.0003), 4)
        slow_ema_sim = 1.1040
    else:
        fast_ema_sim = round(live_bid + random.uniform(-0.15, 0.25), 2)
        slow_ema_sim = 2514.00
        
    market_trend = "BULLISH (UPTREND)" if fast_ema_sim >= slow_ema_sim else "BEARISH (DOWNTREND)"
    active_direction = "BUY LIMIT" if market_trend == "BULLISH (UPTREND)" else "SELL LIMIT"
    rsi_val = round(random.uniform(25.0, 78.0), 2)
    rsi_filter_block = False
    
    if rsi_val >= 70.0:
        rsi_filter_block = True if active_direction == "BUY LIMIT" else False
    elif rsi_val <= 30.0:
        rsi_filter_block = True if active_direction == "SELL LIMIT" else False

    max_drawdown_limit_pct = 5.0
    simulated_starting_equity = 175.00  
    current_drawdown_pct = round(((simulated_starting_equity - balance) / simulated_starting_equity) * 100.0, 2)
    drawdown_lock_engaged = current_drawdown_pct >= max_drawdown_limit_pct

    simulated_filled_entry = live_bid - 1.5 if "BUY" in active_direction else live_bid + 1.5
    simulated_target_tp = simulated_filled_entry + 6.0 if "BUY" in active_direction else simulated_filled_entry - 6.0
    simulated_target_sl = simulated_filled_entry - 3.0 if "BUY" in active_direction else simulated_filled_entry + 3.0
    
    execution_state = "RUNNING_ACTIVE"
    simulated_pnl = (live_bid - simulated_filled_entry) * 50.0 if "BUY" in active_direction else (simulated_filled_entry - live_bid) * 50.0
    
    positions_matrix = [
        {
            "Ticket ID": "MT5-8834921", "Instrument": sym_str, "Direction": "BUY (LONG)" if active_direction == "BUY LIMIT" else "SELL (SHORT)",
            "Volume Lots": 0.50, "Entry Price": f"${simulated_filled_entry:,.2f}", "Current Price": f"${live_bid:,.2f}",
            "TP Target": f"${simulated_target_tp:,.2f}", "SL Target": f"${simulated_target_sl:,.2f}",
            "Status Matrix": execution_state, "Net Floating PnL": f"${simulated_pnl:,.2f}"
        }
    ]
    
    return {
        "status": "PROCESSING", "active_symbol": sym_str, "live_bid": live_bid, "live_ask": live_ask,
        "fast_ema": fast_ema_sim, "slow_ema": slow_ema_sim, "market_trend": market_trend, "rsi": rsi_val, "rsi_filter_block": rsi_filter_block,
        "positions_matrix": positions_matrix, "drawdown_lock_engaged": drawdown_lock_engaged, "current_drawdown_pct": current_drawdown_pct
    }
