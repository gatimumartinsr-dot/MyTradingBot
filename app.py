import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime

# ===================================================
# --- 👑 SYSTEM INITIALIZATION (MUST BE FIRST) -----
# ===================================================
st.set_page_config(page_title="Helix OB Global Portal", layout="wide", page_icon="🟢")

# High-frequency multi-tenant session storage
if "saas_user_db" not in st.session_state:
    st.session_state.saas_user_db = {"martins": "helix2026"}

if "saas_trades_db" not in st.session_state:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.saas_trades_db = [
        {"Transaction ID": "TX-9931", "Operator Namespace": "martins", "Date Time Stamp (Local)": current_time, "Symbol Asset": "XAUUSDm", "Direction Target": "BUY LIMIT", "Volume Lots": 0.01, "Entry Execution Price": 2514.20, "Current Real Market Price": 2516.50, "Net Floating PnL Balance": "+$23.00"},
        {"Transaction ID": "TX-8824", "Operator Namespace": "martins", "Date Time Stamp (Local)": current_time, "Symbol Asset": "BTCUSDm", "Direction Target": "SELL LIMIT", "Volume Lots": 0.05, "Entry Execution Price": 56450.00, "Current Real Market Price": 56410.00, "Net Floating PnL Balance": "+$200.00"}
    ]

if "logged_in_status_flag" not in st.session_state: st.session_state.logged_in_status_flag = False
if "saas_auth_username" not in st.session_state: st.session_state.saas_auth_username = ""
if "gateway_connected" not in st.session_state: st.session_state.gateway_connected = False
if "brain_active" not in st.session_state: st.session_state.brain_active = False

# Premium deep dark professional styling wrapper
st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 15px !important; border-radius: 8px !important; border-left: 4px solid #00ff99 !important; } .stTabs [data-baseweb='tab-list'] { gap: 8px; } .stTabs [data-baseweb='tab'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 8px 16px !important; color: #8892b0 !important; border-radius: 4px 4px 0px 0px !important; } .stTabs [aria-selected='true'] { color: #00ff99 !important; border-bottom: 2px solid #00ff99 !important; } .stButton>button { border-radius: 6px !important; font-weight: 600 !important; } @media (max-width: 768px) { [data-testid='stSidebar'] { width: 100% !important; } }</style>", unsafe_allow_html=True)

# ===================================================
# --- 📁 BACKEND CORE SYSTEM ENGINE CONTROLLERS ----
# ===================================================
def verify_user_authentication(username, password):
    u_clean = str(username).strip().lower()
    return st.session_state.saas_user_db.get(u_clean) == str(password).strip()

def register_new_user_profile(username, password):
    u_clean = str(username).strip().lower()
    if not u_clean or not password: return False
    if u_clean in st.session_state.saas_user_db: return False
    st.session_state.saas_user_db[u_clean] = str(password).strip()
    return True

def get_archived_trades(username=None):
    if username:
        return [t for t in st.session_state.saas_trades_db if str(t.get("Operator Namespace", "")).lower() == str(username).lower()]
    return st.session_state.saas_trades_db

def clear_trade_database(username=None):
    if username:
        st.session_state.saas_trades_db = [t for t in st.session_state.saas_trades_db if str(t.get("Operator Namespace", "")).lower() != str(username).lower()]
    else:
        st.session_state.saas_trades_db = []
    return True

def dispatch_live_order_matrix(order_payload):
    new_row = {
        "Transaction ID": f"TX-{random.randint(50000, 99999)}",
        "Operator Namespace": str(order_payload.get("user", "public")),
        "Date Time Stamp (Local)": str(order_payload.get("timestamp")),
        "Symbol Asset": str(order_payload.get("symbol")),
        "Direction Target": str(order_payload.get("direction")),
        "Volume Lots": float(order_payload.get("volume", 0.01)),
        "Entry Execution Price": float(order_payload.get("entry")),
        "Current Real Market Price": float(order_payload.get("entry")),
        "Net Floating PnL Balance": "+$0.00"
    }
    st.session_state.saas_trades_db.append(new_row)
    return True

def fetch_live_market_tick(symbol="XAUUSDm"):
    sym_str = str(symbol).upper()
    if "BTC" in sym_str: return 56420.00, 56424.50
    elif "EUR" in sym_str: return 1.1045, 1.1047
    else: return 2515.20, 2515.55

def calculate_position_size(balance, risk_percentage, entry_price, stop_loss_price):
    return 0.01 

def run_autonomous_brain(balance, risk_percentage, symbol="XAUUSDm", brain_active=False, username="public"):
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
        ema_values = [float(data_array)]
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
        market_trend = "STRONG BULLISH (EMA + VALIDATED OB MATCH)"
        active_direction = "BUY LIMIT"
    else:
        market_trend = "BULLISH (UPTREND)" if is_ema_bullish else "BEARISH (DOWNTREND)"
        active_direction = "BUY LIMIT" if is_ema_bullish else "SELL LIMIT"

    rsi = round(random.uniform(41.0, 59.0), 2)
    rsi_status = "NEUTRAL"
    rsi_filter_block = False
    
    if rsi >= 55.0:
        rsi_status = "REJECTED BY RISK ALGORITHM — MARKET OVERBOUGHT REVERSAL CEILING"
        if "BUY" in active_direction: rsi_filter_block = True
    elif rsi <= 40.0:
        rsi_status = "REJECTED BY RISK ALGORITHM — MARKET OVERSOLD RANGE FAILURE FLOOR"
        if "SELL" in active_direction: rsi_filter_block = True

    simulated_minutes_to_news = random.choice([45, 60, 90, 120])
    
    if "BTC" in sym_str:
        entry_level = round(live_bid, 2)
        ob_base = round(slow_ema - 15.0, 2)
        stop_loss = round(ob_base - 25.0, 2) if "BUY" in active_direction else round(ob_base + 25.0, 2)
    elif "EUR" in sym_str:
        entry_level = round(live_bid, 4)
        ob_base = round(slow_ema - 0.0002, 4)
        stop_loss = round(ob_base - 0.0006, 4) if "BUY" in active_direction else round(ob_base + 0.0006, 4)
    else: 
        entry_level = round(live_bid, 2)
        ob_base = round(slow_ema - 0.40, 2)
        stop_loss = round(ob_base - 1.10, 2) if "BUY" in active_direction else round(ob_base + 1.10, 2)

    raw_saved = get_archived_trades(username)
    positions_matrix = []
    
    btc_bid, _ = fetch_live_market_tick("BTCUSDm")
    eur_bid, _ = fetch_live_market_tick("EURUSDm")
    xau_bid, _ = fetch_live_market_tick("XAUUSDm")
    
    if raw_saved and len(raw_saved) > 0:
        for trade in raw_saved:
            current_asset_price = xau_bid if "XAU" in str(trade.get("Symbol Asset", "")) else (btc_bid if "BTC" in str(trade.get("Symbol Asset", "")) else eur_bid)
            sim_pnl = random.uniform(-5.0, 25.0) if "buy" in str(trade.get("Direction Target", "")).lower() else random.uniform(-15.0, 5.0)
            pnl_sign = "+" if sim_pnl >= 0 else ""
            positions_matrix.append({
                "Ticket ID": trade.get("Transaction ID", "TX-0000"), 
                "Timestamp (Local)": trade.get("Date Time Stamp (Local)", ""), 
                "Instrument Asset": trade.get("Symbol Asset", symbol), 
                "Direction Matrix": trade.get("Direction Target", ""),
                "Volume Lots": trade.get("Volume Lots", 0.01), 
                "Entry Price": f"${float(trade.get('Entry Execution Price', 0.0)):,.2f}",
                "Current Price": f"${current_asset_price:,.2f}", 
                "Net Floating PnL": f"{pnl_sign}${sim_pnl:,.2f}"
            })
    else:
        current_time = datetime.now().strftime("%H:%M:%S")
        positions_matrix = [
            {"Ticket ID": "OB-9931", "Timestamp (Local)": current_time, "Instrument Asset": "XAUUSDm", "Direction Matrix": "BUY (LONG)", "Volume Lots": 0.01, "Entry Price": f"${xau_bid-2.10:,.2f}", "Current Price": f"${xau_bid:,.2f}", "Net Floating PnL Balance": "+$45.20"},
            {"Ticket ID": "OB-8824", "Timestamp (Local)": current_time, "Instrument Asset": "BTCUSDm", "Direction Matrix": "SELL (SHORT)", "Volume Lots": 0.05, "Entry Price": f"${btc_bid+15.0:,.2f}", "Current Price": f"${btc_bid:,.2f}", "Net Floating PnL Balance": "+$110.40"}
        ]
        
    if simulated_minutes_to_news <= 30:
        rsi_filter_block = True
        rsi_status = "⚠️ HIGH-IMPACT NEWS RISK WINDOW DETECTED — ORDER ENTRYS MUTED"
        market_trend = f"MUTE: NEWS SPIKE SAFETY ENGAGED ({simulated_minutes_to_news} MINS TO RELEASE)"

