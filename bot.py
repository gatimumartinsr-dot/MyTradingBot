import random
import os
import json

DB_FILE = "trades.json"

def init_trade_database():
    """Initializes the JSON storage layer file if it does not exist yet."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)

def clear_trade_database():
    """Wipes all historical entries inside the database layer."""
    try:
        with open(DB_FILE, "w") as f:
            json.dump([], f)
        return True
    except Exception:
        return False

def fetch_live_market_tick(symbol="XAUUSDm"):
    try:
        base_bid = 2514.11 + random.uniform(-0.5, 0.5)
        spread = round(random.uniform(0.15, 0.45), 2)
        base_ask = base_bid + spread
        return round(base_bid, 2), round(base_ask, 2)
    except Exception as e:
        return 2514.11, 2514.41

def calculate_position_size(balance, risk_percentage, entry_price, stop_loss_price):
    try:
        risk_amount_dollars = balance * (risk_percentage / 100.0)
        points_at_risk = abs(entry_price - stop_loss_price)
        if points_at_risk <= 0:
            return 0.01
        calculated_lots = risk_amount_dollars / points_at_risk
        if calculated_lots < 0.01:
            return 0.01
        return round(calculated_lots, 2)
    except Exception as e:
        return 0.01

def dispatch_live_order_matrix(order_payload):
    try:
        init_trade_database()
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
    except Exception as e:
        return False

def get_archived_trades():
    try:
        init_trade_database()
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def apply_trailing_stop_loss(current_price, entry_price, current_sl, trailing_distance, direction="BUY LIMIT"):
    try:
        if "BUY" in direction:
            if current_price > entry_price:
                new_sl_target = current_price - trailing_distance
                if new_sl_target > current_sl:
                    return round(new_sl_target, 2)
        elif "SELL" in direction:
            if current_price < entry_price:
                new_sl_target = current_price + trailing_distance
                if current_sl == 0 or new_sl_target < current_sl:
                    return round(new_sl_target, 2)
        return current_sl
    except Exception as e:
        return current_sl

def run_autonomous_brain(balance, risk_percentage, symbol="XAUUSDm"):
    try:
        live_bid, live_ask = fetch_live_market_tick(symbol)
        
        fast_ema_sim = round(live_bid + random.uniform(-0.15, 0.25), 2)
        slow_ema_sim = 2514.00
        
        if fast_ema_sim >= slow_ema_sim:
            market_trend = "BULLISH (UPTREND)"
            active_direction = "BUY LIMIT"
        else:
            market_trend = "BEARISH (DOWNTREND)"
            active_direction = "SELL LIMIT"
        
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

        simulated_filled_entry = 2510.00
        simulated_current_sl = 2505.00 if active_direction == "BUY LIMIT" else 2520.00
        trailing_buffer_points = 4.00
        
        new_calculated_sl = apply_trailing_stop_loss(
            current_price=live_bid, entry_price=simulated_filled_entry, current_sl=simulated_current_sl,
            trailing_distance=trailing_buffer_points, direction=active_direction
        )
        
        simulated_pnl = (live_bid - simulated_filled_entry) * 100.0 if active_direction == "BUY LIMIT" else (simulated_filled_entry - live_bid) * 100.0
        pnl_sign = "+" if simulated_pnl >= 0 else ""
        
        positions_matrix = [
            {
                "Ticket ID": "MT5-8834921", "Instrument": symbol, "Direction": "BUY (LONG)" if active_direction == "BUY LIMIT" else "SELL (SHORT)",
                "Volume Lots": 0.50, "Entry Price": f"${simulated_filled_entry:,.2f}", "Current Price": f"${live_bid:,.2f}",
                "Active Stop Loss": f"${new_calculated_sl:,.2f}", "Net Floating PnL": f"{pnl_sign}${simulated_pnl:,.2f}"
            }
        ]
        
        return {
            "status": "PROCESSING", "active_symbol": symbol, "live_bid": live_bid, "live_ask": live_ask,
            "fast_ema": fast_ema_sim, "slow_ema": slow_ema_sim, "market_trend": market_trend, "rsi": rsi_val, "rsi_status": rsi_status,
            "rsi_filter_block": rsi_filter_block, "active_sl": new_calculated_sl, "action_executed": "HOLD" if new_calculated_sl == simulated_current_sl else "STOP_LOSS_TRAILED",
            "positions_matrix": positions_matrix
        }
    except Exception as e:
        return {
            "status": "ERROR", "message": str(e), "live_bid": 2514.11, "live_ask": 2514.41,
            "fast_ema": 2514.20, "slow_ema": 2514.00, "market_trend": "BULLISH (UPTREND)", "rsi": 50.0, "rsi_status": "NEUTRAL",
            "rsi_filter_block": False, "active_sl": 2505.00, "action_executed": "HOLD", "positions_matrix": []
        }
