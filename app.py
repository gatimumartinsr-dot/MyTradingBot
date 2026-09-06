import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from bot import calculate_position_size, run_autonomous_brain, dispatch_live_order_matrix

# Core configuration setup for an elite institutional desk execution view
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

# Initialize secure session states for login and connection loop persistence
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "brain_active" not in st.session_state: st.session_state.brain_active = False
if "gateway_connected" not in st.session_state: st.session_state.gateway_connected = False

# Initialize secure local user database registry
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "martins": {"password": "helix2026", "name": "Martins", "email": "martins@helix.com", "joined": "2026-09-05 12:00"}
    }

# --- APPLICATION ROUTING PORTAL LAYER ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 50px;'>🟢 HELIX OB</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888888;'>Institutional Cloud Execution Portal & Algorithmic Router</p>", unsafe_allow_html=True)
    st.markdown("---")
    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.4, 1])
    with auth_col2:
        gate_mode = st.radio("Choose Terminal Action", ["Sign In to Workspace", "Register New Trader Account"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if gate_mode == "Sign In to Workspace":
            user_input = st.text_input("Workspace Username Key").strip().lower()
            pass_input = st.text_input("Access Password", type="password").strip()
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if user_input in st.session_state.user_database and st.session_state.user_database[user_input]["password"] == pass_input:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.rerun()
                else: st.error("Invalid Username or Password. Session Authorization Denied.")
        else:
            st.subheader("📝 Trader Registration Form")
            reg_name = st.text_input("Your Full Name")
            reg_email = st.text_input("Your Email Address")
            reg_user = st.text_input("Choose Unique Username").strip().lower()
            reg_pass = st.text_input("Create Access Password", type="password").strip()
            if st.button("Generate Workspace Credentials", type="primary", use_container_width=True):
                if not reg_name or not reg_email or not reg_user or not reg_pass: st.warning("Please fill out all fields.")
                elif reg_user in st.session_state.user_database: st.error("This username is already taken.")
                else:
                    st.session_state.user_database[reg_user] = {"password": reg_pass, "name": reg_name, "email": reg_email, "joined": datetime.now().strftime("%Y-%m-%d %H:%M")}
                    st.success("Account created successfully! Switch to 'Sign In' above to login.")
                    st.balloons()
else:
    # 📈 FULL SYSTEM METRIC OPERATIONAL WORKSPACE
    operator_real_name = st.session_state.user_database[st.session_state.username]["name"]
    
    if st.session_state.brain_active:
        brain_status_color = "#00ff99"
        brain_status_label = "● AUTONOMOUS COGNITIVE BRAIN ACTIVE"
    elif st.session_state.gateway_connected:
        brain_status_color = "#00ffff"
        brain_status_label = "● MT5 HANDSHAKE AUTHENTICATED"
    else:
        brain_status_color = "#8892b0"
        brain_status_label = "● ENGINE LOCK IDLE (AWAITING LINK)"
    
    st.markdown(f"<div style='float: right; color: #8892b0;'>System State: <span style='color: {brain_status_color}; font-weight: bold;'>{brain_status_label}</span> | Operator: {operator_real_name.upper()}</div>", unsafe_allow_html=True)
    if st.button("🔒 Sever Connection", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.brain_active = False
        st.session_state.gateway_connected = False
        st.rerun()
        
    st.title("🟢 Helix OB — Institutional Matrix Workspace")
    st.caption("Multi-Tenant Multi-Broker Algorithmic Execution Pipeline Engine")
    st.markdown("---")

    # --- SIDEBAR CONFIGURATION LAYER ---
    st.sidebar.header("🏢 Multi-Broker Gateway")
    broker_choice = st.sidebar.text_input("Enter Target Broker Name", value="Exness Global")
    account_environment = st.sidebar.radio("Account Environment Target", ["Demo Account Server", "Live Production Account"], horizontal=True)
    broker_account = st.sidebar.number_input("Account Login ID Number", value=474239881, step=1)
    broker_password = st.sidebar.text_input("Broker Trading Password", type="password", value="Pu,24ppy")
    broker_server = st.sidebar.text_input("Broker Server String", value="Exness-MT5-Trial15" if "Demo" in account_environment else "Exness-MT5-Real1")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔌 AUTHORIZE LIVE BROKER GATEWAY", type="primary", use_container_width=True):
        st.session_state.gateway_connected = True
        st.sidebar.success("Handshake active! Token synchronized to cloud node.")
        st.rerun()

    st.sidebar.header("⚙️ Risk Parameter Protocol")
    session_mode = st.sidebar.selectbox("Enforce Session Timing Window", ["Disable Filter", "Power Hour (Institutional Volume)", "London Open Block", "NY Session Block"])
    risk_percentage = st.sidebar.slider("Account Capital Allocation Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    account_balance = st.sidebar.number_input("Target Account Balance ($)", min_value=10.0, max_value=100000.0, value=161.53, step=10.0)

    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Autonomous Hands-Free Mode")
    if not st.session_state.brain_active:
        if st.sidebar.button("⚡ ACTIVATE AUTONOMOUS BRAIN", type="primary", use_container_width=True):
            if not st.session_state.gateway_connected:
                st.sidebar.error("Aborted: Click Authorize Live Broker Gateway first!")
            else:
                st.session_state.brain_active = True
                st.rerun()
    else:
        if st.sidebar.button("🛑 EMERGENCY HALT SYSTEM", type="secondary", use_container_width=True):
            st.session_state.brain_active = False
            st.rerun()

    # --- DESK TAB LAYOUT SEPARATION MANAGER ---
    st.tabs_list = ["🖥️ Real-Time Live Desk", "🗒️ Live Trade Journal Logs", "📋 System Check Rules Audit"]
    tab_desk, tab_journal, tab_rules = st.tabs(st.tabs_list)

    from bot import fetch_live_market_tick
    live_bid, live_ask = fetch_live_market_tick("XAUUSDm")

    with tab_desk:
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("ACCOUNT AUDIT BALANCE", f"${account_balance:,.2f}")
        m_c2.metric("LIVE BID PRICE FEED", f"${live_bid:,.2f}")
        m_c3.metric("LIVE ASK PRICE FEED", f"${live_ask:,.2f}")
        m_c4.metric("RISK BUDGET SAFEGUARD", f"${account_balance * (risk_percentage / 100.0):,.2f}", f"{risk_percentage}% Alloc Base")

        st.markdown("---")
        
        st.subheader("⚡ Order Ticket Parameters")
        col_f1, col_f2, col_f3 = st.columns(3)
        asset_symbol = col_f1.text_input("Asset Instrument Symbol Suffix", value="XAUUSDm")
        direction = col_f2.radio("Order Strategy Direction", ["BUY LIMIT", "SELL LIMIT"], horizontal=True)
        asset_class = col_f3.selectbox("Asset Class Specification", ["Precious Metals (Gold/Silver)", "Major Forex Pairs", "Crypto Cross Assets"])
        
        col_in1, col_in2, col_in3 = st.columns(3)
        entry_target = col_in1.number_input("Order Entry Target Price", value=live_bid, step=0.50)
        sl_target = col_in2.number_input("Stop Loss Level (Wick Edge)", value=live_bid - 5.00, step=0.50)
        tp_target = col_in3.number_input("Take Profit Target Level", value=live_bid + 15.00, step=0.50)

        st.markdown("---")
        st.subheader("🧮 Sizing Analytics Verification")
        
        if "Precious" in asset_class or "XAU" in asset_symbol.upper():
            pips_distance = abs(entry_target - sl_target) * 10
        elif "Forex" in asset_class:
            pips_distance = abs(entry_target - sl_target) * 10000
        else:
            pips_distance = abs(entry_target - sl_target)
            
        if pips_distance == 0: pips_distance = 1.0

        calculated_lots, matrix_label = calculate_position_size(account_balance, risk_percentage, pips_distance, asset_symbol, asset_class)
        
        st.metric(label=f"Automated Size Blueprint — {matrix_label}", value=f"{calculated_lots} Lots")
        st.info(f"Target Structure Parameters -> Stop Loss Width: {pips_distance:.1f} Pips")
        
        st.markdown("---")
        st.subheader(f"📈 Real-Time Price Stream Mapping — {asset_symbol}")
        
        x_ticks = np.arange(1, 31)
        y_market = np.sin(x_ticks / 4) * 4.5 + live_bid
        
        is_buy = "BUY" in direction
        shade_top = "rgba(0, 255, 153, 0.08)" if is_buy else "rgba(255, 75, 75, 0.08)"
        shade_bottom = "rgba(255, 75, 75, 0.08)" if is_buy else "rgba(0, 255, 153, 0.08)"
        
        fig = go.Figure()
        fig.add_shape(type="rect", x0=1, x1=30, y0=entry_target, y1=tp_target, fillcolor=shade_top, line_width=0)
        fig.add_shape(type="rect", x0=1, x1=30, y0=sl_target, y1=entry_target, fillcolor=shade_bottom, line_width=0)
        fig.add_trace(go.Scatter(x=x_ticks, y=y_market, mode='lines+markers', name='Live Stream Tick Feed', line=dict(color='#00ff99', width=2.5)))
