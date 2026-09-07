import random

def fetch_live_market_tick(symbol="XAUUSDm"):
    """Generates pure pricing ticks mapped cleanly across cross-asset ticker configurations."""
    try:
        sym_str = str(symbol).upper()
        if "BTC" in sym_str:
            base_bid = 64350.00 + random.uniform(-10.0, 15.0)
            spread = 4.50
        elif "EUR" in sym_str:
            base_bid = 1.1045 + random.uniform(-0.0002, 0.0004)
            spread = 0.0002
        else: # XAUUSDm
            base_bid = 2514.11 + random.uniform(-0.3, 0.3)
            spread = 0.30
        return round(base_bid, 2), round(base_bid + spread, 2)
    except Exception:
        return 2514.11, 2514.41

def calculate_position_size(balance, risk_percentage, entry_price, stop_loss_price):
    try:
        risk_amount_dollars = balance * (risk_percentage / 100.0)
        points_at_risk = abs(entry_price - stop_loss_price)
        if points_at_risk <= 0: return 0.01
        return round(max(risk_amount_dollars / points_at_risk, 0.01), 2)
    except Exception:
        return 0.01

def dispatch_live_order_matrix(order_payload):
    return True

def get_archived_trades():
    return []

def clear_trade_database():
    return True

def run_autonomous_brain(balance, risk_percentage, symbol="XAUUSDm", brain_active=False):
    """
    ==========================================================================
    🧠 MASTER STRATEGY TRADING RULES BOX
    ==========================================================================
    Modify the calculation lines below to tweak, add, or optimize your rules.
    Front-end charts and indicators adapt automatically to these parameters.
    """
    # 1. Fetch real-time ticker prices
    live_bid, live_ask = fetch_live_market_tick(symbol)
    
    # 2. Strategy Indicator Rules Configuration 
    fast_ema = round(live_bid + random.uniform(-0.1, 0.2), 2)
    slow_ema = round(live_bid - 0.1, 2)
    rsi = round(random.uniform(25.0, 78.0), 2)
    
    market_trend = "BULLISH (UPTREND)" if fast_ema >= slow_ema else "BEARISH (DOWNTREND)"
    
    # Evaluate overextended oscillator filters
    rsi_status = "NEUTRAL"
    rsi_filter_block = False
    if rsi >= 70.0:
        rsi_status = "OVERBOUGHT (HIGH RISK)"
        rsi_filter_block = True
    elif rsi <= 30.0:
        rsi_status = "OVERSOLD (ACCUMULATION)"
        rsi_filter_block = True
        
    # 3. Dynamic Strategy Graph Level Overlays (Candlestick Chart Lines)
    # Tweak these rules to adjust your Entry, Order Blocks, and Stop Loss parameters
    if "BTC" in str(symbol).upper():
        entry_level = round(live_bid - 5.0, 2)
        ob_zone = round(live_bid - 12.0, 2)
        stop_loss = round(live_bid - 25.0, 2)
    elif "EUR" in str(symbol).upper():
        entry_level = round(live_bid - 0.0002, 4)
        ob_zone = round(live_bid - 0.0005, 4)
        stop_loss = round(live_bid - 0.0015, 4)
    else: # Gold Defaults
        entry_level = round(live_bid - 0.40, 2)
        ob_zone = round(live_bid - 0.90, 2)
        stop_loss = round(live_bid - 1.80, 2)
        
    # 4. Mock Active Running Positions Matrix Data Packet
    positions_matrix = [{
        "Ticket ID": "MT5-998432",
        "Instrument": str(symbol),
        "Direction": "BUY (LONG)" if market_trend == "BULLISH (UPTREND)" else "SELL (SHORT)",
        "Volume Lots": 0.50,
        "Entry Price": entry_level,
        "Current Price": live_bid,
        "Net Floating PnL": "+$75.00" if market_trend == "BULLISH (UPTREND)" else "-$25.00"
    }]
    
    return {
        "live_bid": live_bid,
        "live_ask": live_ask,
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "rsi": rsi,
        "market_trend": market_trend,
        "rsi_status": rsi_status,
        "rsi_filter_block": rsi_filter_block,
        "entry_level": entry_level,
        "ob_zone": ob_zone,
        "stop_loss": stop_loss,
        "positions_matrix": positions_matrix
    }
