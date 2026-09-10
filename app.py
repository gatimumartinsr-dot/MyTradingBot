import streamlit as st
import pandas as pd
import numpy as np
import random
import time
from datetime import datetime

# ====================================================================
# 1. SYSTEM INITIALIZATION & STATE ENGINE (CRITICAL TOP-LEVEL MATRIX)
# ====================================================================
st.set_page_config(page_title="Helix OB Global Portal", layout="wide", page_icon="🟢")

# Initialize all state flags safely to prevent reset loops on re-run
if "logged_in_status_flag" not in st.session_state:
    st.session_state["logged_in_status_flag"] = False
if "saas_auth_username" not in st.session_state:
    st.session_state["saas_auth_username"] = ""
if "mt5_connected" not in st.session_state:
    st.session_state["mt5_connected"] = False

# Hardened Session State DB Engine
if "saas_user_db" not in st.session_state:
    st.session_state["saas_user_db"] = {"martins": "helix2026"}

if "saas_trades_db" not in st.session_state:
    st.session_state["saas_trades_db"] = [
        {"Ticket": "TX-9931", "Asset": "XAUUSDm", "Type": "BUY LIMIT", "Lots": 0.01, "Entry": 2514.20, "Status": "Active", "PnL": 23.00, "Timestamp": "2026-09-10 10:14"},
        {"Ticket": "TX-8824", "Asset": "BTCUSDm", "Type": "SELL LIMIT", "Lots": 0.05, "Entry": 56450.00, "Status": "Active", "PnL": 200.00, "Timestamp": "2026-09-10 11:45"}
    ]

if "journal_logs" not in st.session_state:
    st.session_state["journal_logs"] = [
        {"Timestamp": "2026-09-10 09:00", "Event": "System initialized under matrix deployment rule."},
        {"Timestamp": "2026-09-10 10:15", "Event": "TX-9931 successfully validated via internal router."}
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
# 2. INTERFACE SUBSYSTEMS & MIDDLEWARE BACKEND
# ====================================================================
def mt5_node_handshake(login, password, server):
    """
    Placeholder system routing matrix for MetaTrader5 terminal connection.
    Replace this with your physical 'import MetaTrader5 as mt5' nodes down the line.
    """
    if login and password and server:
        time.sleep(0.8) # Simulate structural API validation latency
        return True
    return False

def generate_live_chart_data(symbol):
    """Generates clean real-time pseudo-market arrays for analytical plots."""
    np.random.seed(42)
    base_price = 2515.00 if "XAU" in symbol else (56400.00 if "BTC" in symbol else 1.0850)
    prices = base_price + np.cumsum(np.random.normal(0, base_price * 0.001, 100))
    return pd.DataFrame({"Timeline Tick": range(100), "Price Node ($)": prices})


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
    account_balance = st.sidebar.number_input("Target Account Balance ($)", value=161.53, step=10.0)
    risk_percentage = st.sidebar.slider("Account Capital Exposure Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔗 MT5 Node Stream Integrator")
    
    if not st.session_state["mt5_connected"]:
        mt5_login = st.sidebar.text_input("MT5 Account ID/Login", key="mt5_log")
        mt5_pass = st.sidebar.text_input("MT5 Investor Password", type="password", key="mt5_pwd")
        mt5_server = st.sidebar.text_input("Broker Server (e.g., Exness-Real)", value="Exness-Trial2")
        
        if st.sidebar.button("Link Live MT5 Terminal Node", use_container_width=True):
            if mt5_node_handshake(mt5_login, mt5_pass, mt5_server):
                st.session_state["mt5_connected"] = True
                st.session_state["journal_logs"].append({"Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'), "Event": f"Connected to MT5 Broker Node via Server: {mt5_server}"})
                st.sidebar.success("MT5 stream connected successfully!")
                st.rerun()
            else:
                st.sidebar.error("Handshake rejected. Verify system login credentials.")
    else:
        st.sidebar.success("✅ MT5 Node Protocol: ACTIVE")
        if st.sidebar.button("Sever Terminal Node", use_container_width=True):
            st.session_state["mt5_connected"] = False
            st.session_state["journal_logs"].append({"Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'), "Event": "MT5 Terminal Node manually decoupled."})
            st.rerun()

    # --- MAIN COMPONENT METRICS GRID ---
    m_c1, m_c2, m_c3 = st.columns(3)
    m_c1.metric(label="ACCOUNT BALANCE CONTEXT", value=f"${account_balance:,.2f}")
    m_c2.metric(label="TRACKED ASSET FOCUS", value=str(symbol_choice))
    m_c3.metric(label="RISK ALLOCATION SAFEGUARD", value=f"{risk_percentage}% Layer")
    
    # --- MODULE APP ROUTING CHANNELS (TABS) ---
    tab_desk, tab_charts, tab_journal = st.tabs(["Live Trading Desk", "Market Analytics Charts", "Personal Journal Logs"])
    
    # TAB 1: WORKSTATION EXECUTION DESK
    with tab_desk:
        st.markdown("<br>### Live Open Position Matrix Grid", unsafe_allow_html=True)
        trades_df = pd.DataFrame(st.session_state["saas_trades_db"])
        
        # Displaying active records clearly
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        
        st.markdown("<br>### Manual Order Dispatch Gateway Router", unsafe_allow_html=True)
        o_c1, o_c2, o_c3 = st.columns([2, 2, 1])
        direction = o_c1.radio("Transaction Vector Direction", ["BUY LIMIT", "SELL LIMIT"], horizontal=True)
        
        default_price = 2515.20 if "XAU" in symbol_choice else (56420.00 if "BTC" in symbol_choice else 1.0855)
        entry_input = o_c2.number_input("Target Entry Price", value=default_price, format="%.5f")
        lot_size = o_c3.number_input("Lot Volume Size", value=0.01, step=0.01, format="%.2f")
        
        if st.button("🚀 TRANSMIT ORDER MATRIX TO MT5 LIVE NODE", type="primary", use_container_width=True):
            new_trade = {
                "Ticket": f"TX-{random.randint(50000, 99999)}",
                "Asset": symbol_choice,
                "Type": direction,
                "Lots": lot_size,
                "Entry": entry_input,
                "Status": "Pending" if "LIMIT" in direction else "Active",
                "PnL": 0.00,
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            st.session_state["saas_trades_db"].append(new_trade)
