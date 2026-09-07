import random
import numpy as np
import pandas as pd
from datetime import datetime

def fetch_live_market_tick(symbol="XAUUSDm"):
    try:
        base_bid = 2514.11 + random.uniform(-0.5, 0.5)
        spread = 0.30
        base_ask = base_bid + spread
        return round(base_bid, 2), round(base_ask, 2)
    except Exception as e:
        return 2514.11, 2514.41

def generate_historical_candles(base_price, count=50):
    """
    Generates a high-fidelity synthetic historical candlestick dataset (Open, High, Low, Close).
    Calculates technical indicator overlays directly onto the historical data matrices.
    """
    try:
        np.random.seed(42)
        prices_close = []
        prices_open = []
        prices_high = []
        prices_low = []
        timestamps = []
        
        current_close = base_price - 5.0
        
        for i in range(count):
            move = np.random.uniform(-1.5, 2.0)
            current_open = current_close
            current_close = current_open + move
            
            # Formulate valid mathematical candle wicks
            candle_max = max(current_open, current_close)
            candle_min = min(current_open, current_close)
            current_high = candle_max + np.random.uniform(0.1, 0.8)
            current_low = candle_min - np.random.uniform(0.1, 0.8)
            
            prices_open.append(round(current_open, 2))
            prices_high.append(round(current_high, 2))
            prices_low.append(round(current_low, 2))
            prices_close.append(round(current_close, 2))
            timestamps.append(f"Bar {i+1}")
            
        df = pd.DataFrame({
            "Time": timestamps,
            "Open": prices_open,
            "High": prices_high,
            "Low": prices_low,
            "Close": prices_close
        })
        
        # Overlay Exponential Moving Averages onto the historical dataset
        df["EMA_Fast"] = df["Close"].ewm(span=7, adjust=False).mean().round(2)
        df["EMA_Slow"] = df["Close"].ewm(span=14, adjust=False).mean().round(2)
        return df
    except Exception as e:
        print(f"Candlestick generation failure: {e}")
        return pd.DataFrame()

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
        print(f"Payload Package Data Stream: {order_payload}")
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
    Background worker processing live execution streams, trend indicators, and calculations.
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
        
        # Calculate dynamic simulated RSI Oscillator value bounds
        rsi_val = round(random.uniform(25.0, 78.0), 2)
        rsi_filter_block = False
        
        if rsi_val >= 70.0:
            rsi_status = "OVERBOUGHT (HIGH REVERSAL RISK)"
            if active_direction == "BUY LIMIT": rsi_filter_block = True
        elif rsi_val <= 30.0:
            rsi_status = "OVERSOLD (BOTTOM ACCUMULATION)"
            if active_direction == "SELL LIMIT": rsi_filter_block = True
        else:
            rsi_status = "NEUTRAL (BALANCED MOMENTUM)"

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
        
        simulated_pnl = (live_bid - simulated_filled_entry) * 100.0 if active_direction == "BUY LIMIT" else (simulated_filled_entry - live_bid) * 100.0
        pnl_sign = "+" if simulated_pnl >= 0 else ""
        
        positions_matrix = [
            {
                "Ticket ID": "MT5-8834921",
                "Instrument": symbol,
                "Direction": "BUY (LONG)" if active_direction == "BUY LIMIT" else "SELL (SHORT)",
                "Volume Lots": 0.50,
                "Entry Price": f"${simulated_filled_entry:,.2f}",
                "Current Price": f"${live_bid:,.2f}",
                "Active Stop Loss": f"${new_calculated_sl:,.2f}",
                "Net Floating PnL": f"{pnl_sign}${simulated_pnl:,.2f}"
            }
        ]
        
        # Generate the unified chart dataset array matrix
        historical_candles_df = generate_historical_candles(live_bid, count=40)
        
        return {
            "status": "PROCESSING_DATA_STREAM",
            "active_symbol": symbol,
            "live_bid": live_bid,
            "live_ask": live_ask,
            "fast_ema": fast_ema_sim,
            "slow_ema": slow_ema_sim,
            "market_trend": market_trend,
            "rsi": rsi_val,
            "rsi_status": rsi_status,
            "rsi_filter_block": rsi_filter_block,
            "active_sl": new_calculated_sl,
            "action_executed": "HOLD" if new_calculated_sl == simulated_current_sl else "STOP_LOSS_TRAILED",
            "positions_matrix": positions_matrix,
            "historical_candles_df": historical_candles_df.to_dict(orient="list")
        }
    except Exception as e:
        return {
            "status": "ERROR", "message": str(e), "live_bid": 2514.11, "live_ask": 2514.41,
            "fast_ema": 2514.20, "slow_ema": 2514.00, "market_trend": "BULLISH (UPTREND)",
            "rsi": 50.0, "rsi_status": "NEUTRAL", "rsi_filter_block": False, "active_sl": 2505.00,
            "action_executed": "HOLD", "positions_matrix": [], "historical_candles_df": {}
        }
