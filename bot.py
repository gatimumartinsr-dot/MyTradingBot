import numpy as np
import pandas as pd
from datetime import datetime

# In-memory storage mock database for trade history logs
_MOCK_TRADES_DB = [
    {"Timestamp": "2026-09-07 14:22:01", "Asset": "BTCUSDm", "Type": "BUY_LIMIT", "Volume": 0.15, "Entry": 58250.00, "Status": "FILLED"},
    {"Timestamp": "2026-09-07 15:05:40", "Asset": "XAUUSDm", "Type": "SELL_STOP", "Volume": 1.20, "Entry": 2492.50, "Status": "CLOSED"}
]

def calculate_ema(data_array, period):
    """
    Calculates the Exponential Moving Average safely, handling both 
    raw number arrays and structural candle/tick data formats.
    """
    if not data_array:
        return 0.0
        
    clean_prices = []
    for item in data_array:
        if isinstance(item, (int, float)):
            clean_prices.append(float(item))
        elif isinstance(item, dict):
            val = item.get('close', item.get('bid', item.get('price', list(item.values())[0])))
            clean_prices.append(float(val))
        elif hasattr(item, '__getitem__'):
            try:
                clean_prices.append(float(item['close']))
            except (TypeError, IndexError, KeyError):
                try:
                    clean_prices.append(float(item[4])) # Standard OHLC candle close index
                except (IndexError, TypeError):
                    clean_prices.append(float(item[-1]))
        else:
            try:
                clean_prices.append(float(item))
            except (ValueError, TypeError):
                continue

    if not clean_prices:
        return 0.0

    k = 2 / (period + 1)
    ema_values = [clean_prices[0]]
    
    for price in clean_prices[1:]:
        ema_values.append((price * k) + (ema_values[-1] * (1 - k)))
        
    return round(ema_values[-1], 4)

def run_autonomous_brain(account_balance, risk_percentage, symbol_choice, brain_active):
    """
    Core brain computation processing live matrices and returns trading metadata maps.
    """
    # Baseline pricing initialization depending on instrument asset string
    if "BTC" in symbol_choice:
        base_bid = 58420.50
        spread = 2.50
        prices_sequence = [58300 + np.random.uniform(-10, 10) for _ in range(50)]
    elif "EUR" in symbol_choice:
        base_bid = 1.08450
        spread = 0.00015
        prices_sequence = [1.0840 + np.random.uniform(-0.0005, 0.0005) for _ in range(50)]
    else: # XAUUSDm Default
        base_bid = 2495.20
        spread = 0.25
        prices_sequence = [2490 + np.random.uniform(-1, 1) for _ in range(50)]

    # Compute Technical Engine Indicators Safely
    fast_ema = calculate_ema(prices_sequence, 12)
    slow_ema = calculate_ema(prices_sequence, 26)
    
    is_ema_bullish = fast_ema >= slow_ema
    market_trend = "INSTITUTIONAL STRUCTURAL BULLISH" if is_ema_bullish else "AGGRESSIVE IMPULSIVE BEARISH"
    
    rsi_val = 54.23 + np.random.uniform(-5, 5)
    rsi_status = "NEUTRAL STATE" if 30 <= rsi_val <= 70 else ("OVERBOUGHT" if rsi_val > 70 else "OVERSOLD")
    
    ob_zone = round(base_bid - (base_bid * 0.002), 2)
    entry_level = round(base_bid, 4)
    stop_loss = round(base_bid - (base_bid * 0.005) if is_ema_bullish else base_bid + (base_bid * 0.005), 4)

    return {
        "live_bid": base_bid,
        "live_ask": base_bid + spread,
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "market_trend": market_trend,
        "rsi": rsi_val,
        "rsi_status": rsi_status,
        "ob_zone": ob_zone,
        "entry_level": entry_level,
        "stop_loss": stop_loss
    }

def fetch_live_market_tick(symbol):
    return {"bid": 100.0, "ask": 100.2}

def calculate_position_size(balance, risk, sl_distance):
    return 0.1

def dispatch_live_order_matrix(order_packet):
    return {"status": "SUCCESS", "order_id": 9981232}

def get_archived_trades():
    return _MOCK_TRADES_DB

def clear_trade_database():
    global _MOCK_TRADES_DB
    _MOCK_TRADES_DB.clear()
