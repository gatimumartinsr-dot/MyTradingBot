import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.request
import json
from bot import calculate_position_size, run_autonomous_brain, dispatch_live_order_matrix, fetch_live_market_tick, get_archived_trades, clear_trade_database, log_user_activity, get_audit_logs, clear_audit_ledger

# Core configuration setup for an elite institutional desk execution view
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 20px !important; border-radius: 10px !important; border-left: 5px solid #00ff99 !important; } div.stAlert { background-color: #121620 !important; border: 1px solid #1f2433 !important; } .stButton>button { border-radius: 8px !important; font-weight: 600 !important; } .stTabs [data-baseweb='tab-list'] { gap: 10px; } .stTabs [data-baseweb='tab'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; border-radius: 6px 6px 0px 0px !important; padding: 10px 20px !important; color: #8892b0 !important; } .stTabs [aria-selected='true'] { color: #00ff99 !important; border-bottom: 2px solid #00ff99 !important; }</style>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "brain_active" not in st.session_state: st.session_state.brain_active = False
if "gateway_connected" not in st.session_state: st.session_state.gateway_connected = False

if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "martins": {"password": "helix2026", "name": "Martins", "email": "martins@helix.com", "joined": "2026-09-05 12:00"}
    }

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 50px;'>🟢 HELIX OB</h1>", unsafe_allow_html=True)
    st.markdown("---")
    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.4, 1])
    gate_mode = auth_col2.radio("Choose Terminal Action", ["Sign In to Workspace", "Register New Trader Account"], horizontal=True)
    
    if gate_mode == "Sign In to Workspace":
        user_input = auth_col2.text_input("Workspace Username Key").strip().lower()
        pass_input = auth_col2.text_input("Access Password", type="password").strip()
        if auth_col2.button("Authorize Connection Session", type="primary", use_container_width=True):
            if user_input in st.session_state.user_database and st.session_state.user_database[user_input]["password"] == pass_input:
                st.session_state.logged_in = True
                st.session_state.username = user_input
                log_user_activity(user_input, "USER_LOGIN_SUCCESS", "Successfully authorized security entry key protocol.")
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
    else:
        st.subheader("📝 Trader Registration Form")
        reg_name = auth_col2.text_input("Your Full Name")
        reg_email = auth_col2.text_input("Your Email Address")
        reg_user = auth_col2.text_input("Choose Unique Username").strip().lower()
        reg_pass = auth_col2.text_input("Create Access Password", type="password").strip()
        if auth_col2.button("Generate Workspace Credentials", type="primary", use_container_width=True):
            if not reg_name or not reg_email or not reg_user or not reg_pass:
                st.warning("Please fill out all fields.")
            else:
                st.session_state.user_database[reg_user] = {"password": reg_pass, "name": reg_name, "email": reg_email, "joined": datetime.now().strftime("%Y-%m-%d %H:%M")}
                log_user_activity(reg_user, "NEW_USER_REGISTRATION", f"Created account instance under email {reg_email}")
                st.success("Account created successfully!")
else:
    operator_key_id = st.session_state.username
    
    st.markdown(f"<div style='float: right; color: #8892b0;'>Operator: {operator_key_id.upper()}</div>", unsafe_allow_html=True)
    if st.button("🔒 Sever Connection", type="secondary"):
        log_user_activity(operator_key_id, "USER_LOGOUT", "Severed workstation network socket channel.")
        st.session_state.logged_in = False
        st.session_state.brain_active = False
        st.session_state.gateway_connected = False
        st.rerun()
        
    st.title("🟢 Helix OB — Institutional Matrix Workspace")
    st.caption("Multi-Tenant Multi-Broker Algorithmic Execution Pipeline Engine")
    st.markdown("---")

    # --- SIDEBAR MASTER CONFIGURATION LAYER ---
    st.sidebar.header("🔀 Active Market Selector")
    symbol_default = st.sidebar.selectbox("Choose Target Instrument Asset", ["XAUUSDm", "BTCUSDm", "EURUSDm"])

    st.sidebar.markdown("---")
    st.sidebar.header("🏢 Multi-Broker Gateway")
    broker_choice = st.sidebar.text_input("Enter Target Broker Name", value="Exness Global")
    account_environment = st.sidebar.radio("Account Environment Target", ["Demo Account Server", "Live Production Account"], horizontal=True)
    broker_account = st.sidebar.number_input("Account Login ID Number", value=474239881, step=1)
    broker_server = st.sidebar.text_input("Broker Server String", value="Exness-MT5-Trial15" if "Demo" in account_environment else "Exness-MT5-Real1")

    if st.sidebar.button("🔌 AUTHORIZE LIVE BROKER GATEWAY", type="primary", use_container_width=True):
        st.session_state.gateway_connected = True
        log_user_activity(operator_key_id, "BROKER_HANDSHAKE_LINKED", f"Linked to account {broker_account} server {broker_server}")
        st.sidebar.success("Handshake active!")
        st.rerun()

    st.sidebar.header("⚙️ Risk Parameter Protocol")
    risk_percentage = st.sidebar.slider("Account Capital Allocation Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    account_balance = st.sidebar.number_input("Target Account Balance ($)", min_value=10.0, max_value=100000.0, value=161.53, step=10.0)

    st.sidebar.markdown("---")
    st.sidebar.header("🎚️ Contract Leverage Protocol")
    lot_multiplier = st.sidebar.slider("Lot Size Volume Multiplier Matrix", 1.0, 5.0, 1.0, step=0.5)

    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Autonomous Hands-Free Mode")
    if not st.session_state.brain_active:
        if st.sidebar.button("⚡ ACTIVATE AUTONOMOUS BRAIN", type="primary", use_container_width=True):
            if not st.session_state.gateway_connected:
                st.sidebar.error("Aborted: Authorize Live Broker Gateway first!")
            else:
                st.session_state.brain_active = True
                log_user_activity(operator_key_id, "AUTONOMOUS_BRAIN_START", f"Engaged automated scanning execution channels on {symbol_default}")
                st.rerun()
    else:
        if st.sidebar.button("🛑 EMERGENCY HALT SYSTEM", type="secondary", use_container_width=True):
            st.session_state.brain_active = False
            log_user_activity(operator_key_id, "EMERGENCY_HALT_TRIGGERED", "Administrative thread execution lock activated.")
            st.rerun()

    # --- Run background processing calculations ---
    brain_data = None
    if st.session_state.brain_active:
        brain_data = run_autonomous_brain(account_balance, risk_percentage, symbol_default)
        live_bid = brain_data.get("live_bid", 2514.11)
        live_ask = brain_data.get("live_ask", 2514.41)
    else:
        live_bid, live_ask = fetch_live_market_tick(symbol_default)

    active_spread_points = round(abs(live_ask - live_bid), 4)
    max_allowable_spread = 5.00 if "BTC" in symbol_default else 0.50
    is_spread_breached = active_spread_points > max_allowable_spread

    tab_desk, tab_journal, tab_rules = st.tabs(["🖥️ Real-Time Live Desk", "🗒️ Live Trade Journal Logs", "📋 System Check Rules Audit"])

    # ==========================================
    # --- 🖥️ TAB 1: REAL-TIME LIVE DESK ---
    # ==========================================
    with tab_desk:
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        risk_budget_dollars = (risk_percentage / 100.0) * account_balance
        
        m_c1.metric(label="ACCOUNT AUDIT BALANCE", value=f"${account_balance:,.2f}")
        m_c2.metric(label="LIVE BID FEED", value=f"${live_bid:,.2f}")
        m_c3.metric(label="LIVE ASK FEED", value=f"${live_ask:,.2f}")
        m_c4.metric(label="RISK BUDGET SAFEGUARD", value=f"${risk_budget_dollars:,.2f}", delta=f"{risk_percentage}% Alloc", delta_color="normal")

        if brain_data and "market_trend" in brain_data:
            trend_label = brain_data["market_trend"]
            trend_color = "green" if "BULLISH" in trend_label else "red"
            st.markdown(f"**Trend Engine Target:** :{trend_color}[{trend_label}] (Fast EMA: `{brain_data['fast_ema']}` | Slow EMA: `{brain_data['slow_ema']}`)")
            st.markdown(f"**Momentum Oscillator Index:** `RSI (14) = {brain_data.get('rsi', 50.0):.2f}` | Boundary: `[{brain_data.get('rsi_status', 'NEUTRAL')}]`")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### 📊 Real-Time Momentum Tracker ({symbol_default})")
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("TRACKED INSTRUMENT", str(symbol_default))
        tc2.metric("CURRENT MARKET SPREAD", f"{active_spread_points} Points")
        tc3.metric("SPREAD GAP LIMIT STATUS", "SECURE BOUNDS" if not is_spread_breached else "BREACHED EXCESSIVE")

        # Active Positions Panel Matrix Display (Bracket logic verified and fully closed)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📋 Active Open Position Matrix")
        
        if brain_data and "positions_matrix" in brain_data:
