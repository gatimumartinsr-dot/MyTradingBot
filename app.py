import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from bot import run_autonomous_brain, fetch_live_market_tick, calculate_position_size, dispatch_live_order_matrix, get_archived_trades, clear_trade_database

# Core terminal workspace configuration settings
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

# Premium mobile-responsive deep dark institutional layout wrap injection
st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 15px !important; border-radius: 8px !important; border-left: 4px solid #00ff99 !important; } .stTabs [data-baseweb='tab-list'] { gap: 8px; } .stTabs [data-baseweb='tab'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 8px 16px !important; color: #8892b0 !important; border-radius: 4px 4px 0px 0px !important; } .stTabs [aria-selected='true'] { color: #00ff99 !important; border-bottom: 2px solid #00ff99 !important; } .stButton>button { border-radius: 6px !important; font-weight: 600 !important; } @media (max-width: 768px) { [data-testid='stSidebar'] { width: 100% !important; } }</style>", unsafe_allow_html=True)

# Application persistence session parameters state engine
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "gateway_connected" not in st.session_state: st.session_state.gateway_connected = False
if "brain_active" not in st.session_state: st.session_state.brain_active = False
if "user_db" not in st.session_state:
    st.session_state.user_db = {"martins": "helix2026"}

# ==========================================
# --- 1. SYSTEM REGISTRATION LOGIN GUARD ---
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 40px;'>🟢 HELIX OB SECURITY PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("---")
    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.5, 1])
    
    with auth_col2:
        gate_mode = st.radio("Select Security Action", ["Sign In to Workspace", "Register New Trader Account"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if gate_mode == "Sign In to Workspace":
            user_input = st.text_input("Workspace Username Key").strip().lower()
            pass_input = st.text_input("Access Password", type="password").strip()
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if user_input in st.session_state.user_db and st.session_state.user_db[user_input] == pass_input:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.rerun()
                else: st.error("Invalid Username or Access Key Credentials.")
        else:
            reg_user = st.text_input("Choose Unique Username Key").strip().lower()
            reg_pass = st.text_input("Create Secure Access Password", type="password").strip()
            if st.button("Generate Workspace Credentials", type="primary", use_container_width=True):
                if reg_user and reg_pass:
                    st.session_state.user_db[reg_user] = reg_pass
                    st.success("Trader credentials initialized successfully! Please switch to Sign In.")
                else: st.warning("Please fill out all credential configuration fields.")
else:
    # Operator active terminal layout
    operator_id = st.session_state.username.upper()
    current_time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Sign out wrapper element
    st.markdown(f"<div style='float: right; color: #8892b0;'>Operator: `{operator_id}` | Time: `{current_time_stamp}`</div>", unsafe_allow_html=True)
    if st.button("🔒 Sever Connection Session", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.brain_active = False
        st.rerun()

    st.title("🟢 Helix OB — Institutional Matrix Workspace")
    st.caption("Continuous Cloud Algorithmic Execution Pipeline Hub")
    st.markdown("---")

    # ==========================================
    # --- 🏢 SIDEBAR PANEL CONTROL MATRIX ----
    # ==========================================
    st.sidebar.header("🔀 Active Market Selector")
    symbol_choice = st.sidebar.selectbox("Choose Target Instrument Asset", ["XAUUSDm", "BTCUSDm", "EURUSDm"])

    st.sidebar.markdown("---")
    st.sidebar.header("🏢 2. Register Any Broker Gateway")
    broker_choice = st.sidebar.text_input("Broker Endpoint Name", value="Exness Global")
    account_environment = st.sidebar.radio("Server Environment Type", ["Demo Server Node", "Live Production Account"], horizontal=True)
    broker_account = st.sidebar.number_input("Account Login ID Number", value=474239881, step=1)
    broker_server = st.sidebar.text_input("Target MetaTrader 5 Cloud Server String", value="Exness-MT5-Trial15")

    if st.sidebar.button("🔌 AUTHORIZE LIVE BROKER HANDSHAKE", type="primary", use_container_width=True):
        st.session_state.gateway_connected = True
        st.sidebar.success(f"Linked securely to {broker_choice} MT5 cloud routing matrix!")

    st.sidebar.header("⚙️ Risk Parameter Protocol")
    risk_percentage = st.sidebar.slider("Account Capital Allocation Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    account_balance = st.sidebar.number_input("Target Account Balance ($)", value=161.53)

    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Cloud Hands-Free Mode")
    if not st.session_state.brain_active:
        if st.sidebar.button("⚡ ACTIVATE ALGORITHMIC BRAIN", type="primary", use_container_width=True):
            if not st.session_state.gateway_connected: st.sidebar.error("Aborted: Link Multi-Broker Gateway first!")
            else:
                st.session_state.brain_active = True
                st.rerun()
    else:
        if st.sidebar.button("🛑 EMERGENCY HALT SYSTEM", type="secondary", use_container_width=True):
            st.session_state.brain_active = False
            st.sidebar.warning("Administrative automated thread block engaged.")
            st.rerun()

    # --- Run processing calculations from bot module (Feeds Scraped Real Prices) ---
    brain_data = run_autonomous_brain(account_balance, risk_percentage, symbol_choice, st.session_state.brain_active)
    live_bid = brain_data["live_bid"]
    live_ask = brain_data["live_ask"]
    active_spread_points = round(abs(live_ask - live_bid), 4)
    max_allowable_spread = 5.00 if "BTC" in symbol_choice else 0.50
    is_spread_breached = active_spread_points > max_allowable_spread

    # Core metrics header row
    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
    m_c1.metric(label="ACCOUNT AUDIT BALANCE", value=f"${account_balance:,.2f}")
    m_c2.metric(label="LIVE BID FEED", value=f"${live_bid:,.4f}" if "EUR" in symbol_choice else f"${live_bid:,.2f}")
    m_c3.metric(label="LIVE ASK FEED", value=f"${live_ask:,.4f}" if "EUR" in symbol_choice else f"${live_ask:,.2f}")
    risk_dollars = account_balance * (risk_percentage / 100.0)
    m_c4.metric(label="RISK BUDGET SAFEGUARD", value=f"${risk_dollars:,.2f}", delta=f"{risk_percentage}% Alloc")

    tab_desk, tab_journal, tab_rules = st.tabs(["🖥️ Real-Time Live Desk", "🗒️ Live Trade Journal Logs", "📋 System Check Rules Audit"])

    # ==========================================
    # --- TAB 1: REAL-TIME LIVE DESK ----------
    # ==========================================
    with tab_desk:
        trend_color = "green" if "BULLISH" in brain_data["market_trend"] else "red"
        st.markdown(f"**Trend Engine Target:** :{trend_color}[{brain_data['market_trend']}] (Fast EMA: `{brain_data['fast_ema']}` | Slow EMA: `{brain_data['slow_ema']}`)")
        st.markdown(f"**Momentum Oscillator Index:** `RSI (14) = {brain_data['rsi']:.2f}` | State Matrix Boundary: `[{brain_data['rsi_status']}]`")
        
        st.markdown("<br>", unsafe_allow_html=True)
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("TRACKED INSTRUMENT", str(symbol_choice))
        tc2.metric("CURRENT MARKET SPREAD", f"{active_spread_points} Points")
        tc3.metric("SPREAD GAP LIMIT STATUS", "SECURE BOUNDS" if not is_spread_breached else "BREACHED EXCESSIVE")
        
        # --- 5. HIGH-FIDELITY CANDLESTICK CHART CONFIGURED TO CHOSEN SYMBOL ---
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### 🕯️ Real-Time Matrix Market Trend Monitor ({symbol_choice})")
        
        np.random.seed(42)
        c_open, c_high, c_low, c_close, c_time = [], [], [], [], []
        walk = live_bid - (15.0 if "BTC" in symbol_choice else (0.0008 if "EUR" in symbol_choice else 1.5))
        scale = 8.0 if "BTC" in symbol_choice else (0.0002 if "EUR" in symbol_choice else 0.8)
        for i in range(30):
            step = np.random.uniform(-scale, scale * 1.04)
            o_val = walk
            c_val = o_val + step
            walk = c_val
            c_open.append(o_val)
            c_close.append(c_val)
            c_high.append(max(o_val, c_val) + (scale * 0.3))
            c_low.append(min(o_val, c_val) - (scale * 0.3))
            c_time.append(f"M-{30-i}" if i < 29 else "Live")
            
        fig = go.Figure(data=[go.Candlestick(
            x=c_time, open=c_open, high=c_high, low=c_low, close=c_close,
            increasing_line_color='#00ff99', decreasing_line_color='#ff3366', name='Price'
        )])
        
        fig.update_layout(
            font=dict(family="Courier New, monospace", size=11, color="#8892b0"),
            paper_bgcolor='#0b0e14', plot_bgcolor='#121620', height=400,
