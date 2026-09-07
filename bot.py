import random
import os
import json

DB_FILE = "trades.json"
AUDIT_FILE = "audit_log.json"

def init_databases():
    """Initializes the persistent JSON trade tracking and user event audit storage files."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)
    if not os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "w") as f:
            json.dump([], f)

def log_user_activity(operator, event_action, details):
    """Persistently commits a workspace telemetry event to the user audit ledger database sheet."""
    try:
        init_databases()
        with open(AUDIT_FILE, "r") as f:
            logs = json.load(f)
            
        new_log = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Operator Key": str(operator).upper(),
            "Action Parameter": str(event_action),
            "Operational Details": str(details)
        }
        logs.append(new_log)
        with open(AUDIT_FILE, "w") as f:
            json.dump(logs, f, indent=4)
        return True
    except Exception:
        return False

def get_audit_logs():
    """Reads saved user footprint activities directly back into the frontend frame."""
    try:
        init_databases()
        with open(AUDIT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def clear_audit_ledger():
    """Wipes out user event log telemetry histories."""
    try:
        with open(AUDIT_FILE, "w") as f:
            json.dump([], f)
        return True
    except Exception:
        return False

def fetch_live_market_tick(symbol="XAUUSDm"):
    try:
        sym_str = str(symbol).upper()
        if "BTC" in sym_str:
            base_bid = 64350.00 + random.uniform(-25.0, 35.0)
            spread = round(random.uniform(2.50, 5.00), 2)
        elif "EUR" in sym_str:
            base_bid = 1.1045 + random.uniform(-0.0004, 0.0006)
            spread = 0.0002
        else: # XAUUSDm
            base_bid = 2514.11 + random.uniform(-0.5, 0.5)
            spread = 0.30
        base_ask = base_bid + spread
        return round(base_bid, 4), round(base_ask, 4)
    except Exception:
        return 2514.11, 2514.41

def calculate_position_size(balance, risk_percentage, entry_price, stop_loss_price, multiplier=1.0):
    """Computes stop-loss volume equations scaled dynamically by the user allocation multiplier."""
    try:
        risk_amount_dollars = balance * (risk_percentage / 100.0)
        points_at_risk = abs(entry_price - stop_loss_price)
        if points_at_risk <= 0: 
            return 0.01
        base_lots = risk_amount_dollars / points_at_risk
        amplified_lots = base_lots * float(multiplier)
        return round(max(amplified_lots, 0.01), 2)
    except Exception:
        return 0.01

def dispatch_live_order_matrix(order_payload):
    try:
        init_databases()
        with open(DB_FILE, "r") as f:
            trades = json.load(f)
            
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
        with open(DB_FILE, "w") as f:
            json.dump(trades, f, indent=4)
        return True
    except Exception:
        return False

def get_archived_trades():
    try:
        init_databases()
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def clear_trade_database():
    try:
        with open(DB_FILE, "w") as f:
            json.dump([], f)
        return True
    except Exception:
        return False

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
        rsi_status = "OVERBOUGHT (HIGH RISK)"
        if active_direction == "BUY LIMIT": rsi_filter_block = True
    elif rsi_val <= 30.0:
        rsi_status = "OVERSOLD (ACCUMULATION)"
        if active_direction == "SELL LIMIT": rsi_filter_block = True
    else:
        rsi_status = "NEUTRAL (BALANCED)"

    max_drawdown_limit_pct = 5.0
    simulated_starting_equity = 175.00  
    current_drawdown_pct = round(((simulated_starting_equity - balance) / simulated_starting_equity) * 100.0, 2)
    
    drawdown_lock_engaged = False
    if current_drawdown_pct >= max_drawdown_limit_pct:
        drawdown_lock_engaged = True
        rsi_filter_block = True 

    simulated_filled_entry = live_bid - 1.5 if "BUY" in active_direction else live_bid + 1.5
    simulated_target_tp = simulated_filled_entry + 6.0 if "BUY" in active_direction else simulated_filled_entry - 6.0
    simulated_target_sl = simulated_filled_entry - 3.0 if "BUY" in active_direction else simulated_filled_entry + 3.0
    
    execution_state = "RUNNING_ACTIVE"
    simulated_pnl = (live_bid - simulated_filled_entry) * 50.0 if "BUY" in active_direction else (simulated_filled_entry - live_bid) * 50.0
    
    if ("BUY" in active_direction and live_bid >= simulated_target_tp) or ("SELL" in active_direction and live_bid <= simulated_target_tp):
        execution_state = "🟢 TARGET_TP_HIT_CLOSED"
        simulated_pnl = 300.00
    elif ("BUY" in active_direction and live_bid <= simulated_target_sl) or ("SELL" in active_direction and live_bid >= simulated_target_sl):
        execution_state = "🔴 TARGET_SL_BREACHED_CLOSED"
        simulated_pnl = -150.00
        
    pnl_sign = "+" if simulated_pnl >= 0 else ""
    
    positions_matrix = [
        {
            "Ticket ID": "MT5-8834921", "Instrument": sym_str, "Direction": "BUY (LONG)" if active_direction == "BUY LIMIT" else "SELL (SHORT)",
            "Volume Lots": 0.50, "Entry Price": f"${simulated_filled_entry:,.2f}", "Current Price": f"${live_bid:,.2f}",
            "TP Target": f"${simulated_target_tp:,.2f}", "SL Target": f"${simulated_target_sl:,.2f}",
            "Status Matrix": execution_state, "Net Floating PnL": f"{pnl_sign}${simulated_pnl:,.2f}"
        }
    ]
    
    return {
        "status": "PROCESSING", "active_symbol": sym_str, "live_bid": live_bid, "live_ask": live_ask,
        "fast_ema": fast_ema_sim, "slow_ema": slow_ema_sim, "market_trend": market_trend, "rsi": rsi_val, "rsi_status": rsi_status,
        "rsi_filter_block": rsi_filter_block, "action_executed": "HOLD", "positions_matrix": positions_matrix,
        "drawdown_lock_engaged": drawdown_lock_engaged, "current_drawdown_pct": current_drawdown_pct
    }
from datetime import datetime
