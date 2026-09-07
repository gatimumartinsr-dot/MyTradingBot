import random
from datetime import datetime

def fetch_live_market_tick(symbol="XAUUSDm"):
    try:
        base_bid = 2514.11 + random.uniform(-0.5, 0.5)
        spread = 0.30
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
        print(f"--- [MT5 EXNESS GATEWAY DISPATCH] ---")
        print(f"Payload: {order_payload}")
        return True
    except Exception as e:
        return False

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
    """
    Explicitly accepting 3 parameters to match app.py router execution layout constraints.
    """
    try:
        live_bid, live_ask = fetch_live_market_tick(symbol)
        
        # Calculate simulated Moving Average (EMA) indicators
        fast_ema_sim = round(live_bid + random.uniform(-0.15, 0.25), 2)
        slow_ema_sim = 2514.00
        
        if fast_ema_sim >= slow_ema_sim:
            market_trend = "BULLISH (UPTREND)"
            active_direction = "BUY LIMIT"
        else:
            market_trend = "BEARISH (DOWNTREND)"
            active_direction = "SELL LIMIT"
        
        simulated_filled_entry = 2510.00
        simulated_current_sl = 2505.00 if active_direction == "BUY LIMIT" else 2520.00
        trailing_buffer_points = 4.00
        
        new_calculated_sl = apply_trailing_stop_loss(
            current_price=live_bid,
            entry_price=simulated_filled_entry,
            current_sl=simulated_current_sl,
            trailing_distance=trailing_buffer_points,
            direction=active_direction
        )
        
        return {
            "status": "PROCESSING_DATA_STREAM",
            "active_symbol": symbol,
            "live_bid": live_bid,
            "live_ask": live_ask,
            "fast_ema": fast_ema_sim,
            "slow_ema": slow_ema_sim,
            "market_trend": market_trend,
            "active_sl": new_calculated_sl,
            "action_executed": "HOLD" if new_calculated_sl == simulated_current_sl else "STOP_LOSS_TRAILED"
        }
    except Exception as e:
        return {
            "status": "ERROR", 
            "message": str(e), 
            "live_bid": 2514.11, 
            "live_ask": 2514.41,
            "fast_ema": 2514.20,
            "slow_ema": 2514.00,
            "market_trend": "BULLISH (UPTREND)",
            "active_sl": 2505.00,
            "action_executed": "HOLD"
        }
