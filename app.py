import streamlit as st
import pandas as pd
import numpy as np
import random
import time
from datetime import datetime

# --- CRITICAL NATIVE HARDWARE BRIDGES ---
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# ====================================================================
# 1. SYSTEM INITIALIZATION & STATE ENGINE
# ====================================================================
st.set_page_config(page_title="Helix OB Global Portal", layout="wide", page_icon="🟢")

if "logged_in_status_flag" not in st.session_state:
    st.session_state["logged_in_status_flag"] = False
if "saas_auth_username" not in st.session_state:
    st.session_state["saas_auth_username"] = ""
if "mt5_connected" not in st.session_state:
    st.session_state["mt5_connected"] = False

if "saas_user_db" not in st.session_state:
    st.session_state["saas_user_db"] = {"martins": "helix2026"}

if "journal_logs" not in st.session_state:
    st.session_state["journal_logs"] = [
        {"Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'), "Event": "System initialized. Helix Engine Online."}
    ]

# Institutional UI Dark Palette Injector
st.markdown("""
<style>
    html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; }
    div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 15px !important; border-radius: 8px !important; border-left: 4px solid #00ff99 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #121620 !important; border: 1px solid #1f2433 !important; color: #8892b0 !important; padding: 10px 20px !important; border-radius: 4px !important; }
    .stTabs [aria-selected="true"] { border-color: #00ff99 !important; color: #00ff99 !important; }
</style>
""", unsafe_allow_html=True)


# ====================================================================
# 2. METATRADER 5 LIVE BACKEND PIPELINES
# ====================================================================
def mt5_live_connect(login, password, server):
    """Establishes real physical socket binding to target broker terminal."""
    if not MT5_AVAILABLE:
        # Fallback simulation flag if running on an unsupported platform (e.g. Linux cloud)
        return True, "Simulation Mode Active (Package Unavailable natively on this OS)"
    
    # Initialize terminal connection
    if not mt5.initialize():
        return False, f"Initialization Failed: {mt5.last_error()}"
    
    # Attempt account handshake authentication
    login_status = mt5.login(login=int(login), password=password, server=server)
    if login_status:
        return True, "Successfully bound to live broker terminal node."
    else:
        error_code = mt5.last_error()
        mt5.shutdown()
        return False, f"Handshake Rejected. Code: {error_code}"

def fetch_live_positions():
    """Pulls true open orders out of the live initialized MT5 engine."""
    if not MT5_AVAILABLE or not st.session_state["mt5_connected"]:
        # Fallback Mock Data if connection isn't complete
        return [
            {"Ticket": "TX-9931", "Asset": "XAUUSDm", "Type": "BUY LIMIT", "Lots": 0.01, "Entry": 2514.20, "Status": "Active", "PnL": 23.00},
            {"Ticket": "TX-8824", "Asset": "BTCUSDm", "Type": "SELL LIMIT", "Lots": 0.05, "Entry": 56450.00, "Status": "Active", "PnL": 200.00}
        ]
    
    # Query MT5 API directly
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return []
    
    df_list = []
    for pos in positions:
        df_list.append({
            "Ticket": f"TX-{pos.ticket}",
            "Asset": pos.symbol,
            "Type": "BUY" if pos.type == 0 else "SELL",
            "Lots": pos.volume,
            "Entry": pos.price_open,
            "Status": "Live Running",
            "PnL": round(pos.profit, 2)
        })
    return df_list

def transmit_live_order(symbol, order_type, entry_price, volume):
    """Dispatches true transactional payloads to the MT5 broker server."""
    if not MT5_AVAILABLE or not st.session_state["mt5_connected"]:
        return True, f"Mock Order Matrix TX-{random.randint(1000,9999)} simulated."

    # Map frontend types to native MT5 operational variables
    mt5_type = mt5.ORDER_TYPE_BUY_LIMIT if order_type == "BUY LIMIT" else mt5.ORDER_TYPE_SELL_LIMIT
    
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5_type,
        "price": float(entry_price),
        "deviation": 20,
        "magic": 20260910,
        "comment": "Helix Matrix Dispatch Engine",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Execution Refused: {result.comment} (Code: {result.retcode})"
    return True, f"Order successfully filled on live book. Ticket ID: {result.order}"

def get_live_ticks(symbol):
    """Pulls actual real-time bar matrices to render charts."""
    if not MT5_AVAILABLE or not st.session_state["mt5_connected"]:
        # Fallback visual matrix
        np.random.seed(42)
        base = 2515.00 if "XAU" in symbol else (56400.00 if "BTC" in symbol else 1.0850)
        prices = base + np.cumsum(np.random.normal(0, base * 0.0005, 50))
        return pd.DataFrame({"Timeline Tick": range(50), "Price Node ($)": prices})
    
    # Fetch real technical candle arrays
    rates = mt5.copy_rates_from_now(symbol, mt5.TIMEFRAME_M1, 50)
    if rates is None:
        return pd.DataFrame()
    rates_df = pd.DataFrame(rates)
    rates_df['time'] = pd.to_datetime(rates_df['time'], unit='s')
    return rates_df.rename(columns={'time': 'Timeline Tick', 'close': 'Price Node ($)'})


# ====================================================================
# 3. ROUTER MATRIX LAYER
# ====================================================================

# GATEWAY A: SECURITY & ACCESS MANAGEMENT PORTAL
if not st.session_state["logged_in_status_flag"]:
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 40px;'>🟢 HELIX OB GLOBAL PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8892b0;'>Multi-Tenant Standalone Algorithmic Workstation</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    _, auth_col, _ = st.columns([1, 1.5, 1])
    with auth_col:
        gate_mode = st.radio("Access Control Mode", ["Sign In to Account", "Create Standalone Account"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        user_input = st.text_input("Username Identifier Key", key="user_field_v10").strip().lower()
        pass_input = st.text_input("Access Password", type="password", key="pass_field_v10").strip()
        
        if gate_mode == "Sign In to Account":
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if st.session_state["saas_user_db"].get(user_input) == pass_input:
                    st.session_state["logged_in_status_flag"] = True
                    st.session_state["saas_auth_username"] = user_input
                    st.session_state["journal_logs"].append({"Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'), "Event": f"Operator '{user_input}' authenticated system access."})
                    st.rerun()
                else:
                    st.error("Invalid credentials or unregistered operator profile key.")
        else:
            if st.button("Generate Standalone Credentials", type="primary", use_container_width=True):
                if user_input and pass_input:
                    if user_input in st.session_state["saas_user_db"]:
                        st.error("Username key is already taken.")
                    else:
                        st.session_state["saas_user_db"][user_input] = pass_input
                        st.success("Account profile compiled successfully! Please select 'Sign In' to connect.")
                else:
                    st.warning("Please specify valid characters.")

# GATEWAY B: AUTHENTICATED SYSTEM COMMAND DESK
else:
    current_user = st.session_state["saas_auth_username"]
    st.markdown(f"<div style='float: right; color: #8892b0; font-family: monospace;'>User Context: <b>{current_user.upper()}</b></div>", unsafe_allow_html=True)
    st.title("🟢 Helix Automated Trading Desk")
    
    # --- SIDEBAR ENGINE: CONTROL SETTINGS & HARDWARE COUPLING ---
    st.sidebar.header("Market Asset Settings")
    symbol_choice = st.sidebar.selectbox("Tracked Target Instrument", ["XAUUSDm", "BTCUSDm", "EURUSDm"])
    
    # Conditional defaults matching physical targets
    default_bal = 161.53 if not MT5_AVAILABLE or not st.session_state["mt5_connected"] else mt5.account_info().balance
    account_balance = st.sidebar.number_input("Target Account Balance ($)", value=float(default_bal), step=50.0)
    risk_percentage = st.sidebar.slider("Account Capital Exposure Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔗 MT5 Node Stream Integrator")
    
    if not st.session_state["mt5_connected"]:
        mt5_login = st.sidebar.text_input("MT5 Account ID/Login", key="mt5_log", value="50239102") # Dynamic template values
        mt5_pass = st.sidebar.text_input("MT5 Investor Password", type="password", key="mt5_pwd")
        mt5_server = st.sidebar.text_input("Broker Server", value="Exness-Trial2")
        
        if st.sidebar.button("Link Live MT5 Terminal Node", use_container_width=True):
            success, msg = mt5_live_connect(mt5_login, mt5_pass, mt5_server)
            if success:
                st.session_state["mt5_connected"] = True
