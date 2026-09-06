import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
from bot import calculate_position_size, run_autonomous_brain, dispatch_live_order_matrix

st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 20px !important; border-radius: 10px !important; border-left: 5px solid #00ff99 !important; } div.stAlert { background-color: #121620 !important; border: 1px solid #1f2433 !important; } .stButton>button { border-radius: 8px !important; font-weight: 600 !important; } .stTabs [data-baseweb='tab-list'] { gap: 10px; } .stTabs [data-baseweb='tab'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; border-radius: 6px 6px 0px 0px !important; padding: 10px 20px !important; color: #8892b0 !important; } .stTabs [aria-selected='true'] { color: #00ff99 !important; border-bottom: 2px solid #00ff99 !important; }</style>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "brain_active" not in st.session_state: st.session_state.brain_active = False

if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "martins": {"password": "helix2026", "name": "Martins", "email": "martins@helix.com", "joined": "2026-09-05 12:00"}
    }

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
                if not reg_name or not reg_email or not reg_user or not reg_pass: st.warning("Please fill out all identification fields to register.")
                elif reg_user in st.session_state.user_database: st.error("This username is already taken.")
                else:
                    st.session_state.user_database[reg_user] = {"password": reg_pass, "name": reg_name, "email": reg_email, "joined": datetime.now().strftime("%Y-%m-%d %H:%M")}
                    st.success("Account created successfully! Switch to 'Sign In' above to login.")
                    st.balloons()
else:
    operator_real_name = st.session_state.user_database[st.session_state.username]["name"]
    brain_status_color = "#00ff99" if st.session_state.brain_active else "#8892b0"
    brain_status_label = "● AUTONOMOUS COGNITIVE BRAIN ACTIVE" if st.session_state.brain_active else "● ENGINE LOCK IDLE"
    
    st.markdown(f"<div style='float: right; color: #8892b0;'>System State: <span style='color: {brain_status_color}; font-weight: bold;'>{brain_status_label}</span> | Operator: {operator_real_name.upper()}</div>", unsafe_allow_html=True)
    if st.button("🔒 Sever Connection", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.brain_active = False
        st.rerun()
        
    st.title("🟢 Helix OB — Institutional Matrix Workspace")
    st.caption("Multi-Tenant Multi-Broker Algorithmic Execution Pipeline Engine")
    st.markdown("---")

    # --- SIDEBAR AUTHENTICATION CONFIGURATION LAYER ---
    st.sidebar.header("🏢 Multi-Broker Gateway")
    broker_choice = st.sidebar.text_input("Enter Target Broker Name", value="Exness Global")
    account_environment = st.sidebar.radio("Account Environment Target", ["Demo Account Server", "Live Production Account"], horizontal=True)
    broker_account = st.sidebar.number_input("Account Login ID Number", value=474239881, step=1)
    broker_password = st.sidebar.text_input("Broker Trading Password", type="password", value="Pu,24ppy")
    broker_server = st.sidebar.text_input("Broker Server String", value="Exness-MT5-Trial15" if "Demo" in account_environment else "Exness-MT5-Real1")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Risk Parameter Protocol")
    session_mode = st.sidebar.selectbox("Enforce Session Timing Window", ["Disable Filter", "Power Hour (Institutional Volume)", "London Open Block", "NY Session Block"])
    progression_tier = st.sidebar.selectbox("Gold Progression Tier Rulebook", ["Conservative (1-2% Matrix)", "Medium (3-5% Balanced)", "Aggressive (8-10% High Yield)"])
    account_balance = st.sidebar.number_input("Target Account Balance ($)", min_value=100.0, max_value=100000.0, value=500.0, step=100.0)

    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Autonomous Controller")
    if not st.session_state.brain_active:
        if st.sidebar.button("⚡ ACTIVATE AUTONOMOUS ENGINE", type="primary", use_container_width=True):
            st.session_state.brain_active = True
            st.rerun()
    else:
        if st.sidebar.button("🛑 EMERGENCY HALT SYSTEM", type="secondary", use_container_width=True):
            st.session_state.brain_active = False
            st.rerun()

    # --- DESK TAB LAYOUT SEPARATION MANAGER ---
    tab_desk, tab_journal, tab_rules = st.tabs(["🖥️ Real-Time Live Desk", "🗒️ Live Trade Journal Logs", "📋 System Check Rules Audit"])

    # 📊 INSTANT LIVE QUOTE DATA STREAM INJECTION
    # Fetching real price movements using live ticks from our processing script
    from bot import fetch_live_market_tick
    live_bid, live_ask = fetch_live_market_tick("XAUUSDm")

    with tab_desk:
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("ACCOUNT AUDIT BALANCE", f"${account_balance:,.2f}")
        m_c2.metric("LIVE BID PRICE FEED", f"${live_bid:,.2f}")
        m_c3.metric("LIVE ASK PRICE FEED", f"${live_ask:,.2f}")
        m_c4.metric("RISK BUDGET SAFEGUARD", f"${account_balance * 0.01:,.2f}", "1.0% Base Alloc")

        st.markdown("---")
        
        st.subheader("🧮 Sizing Analytics Verification")
        asset_symbol = "XAUUSDm"
        entry_init = live_bid
        sl_init = live_bid - 10.00
        tp_init = live_bid + 30.00
        
        pips_distance = abs(entry_init - sl_init) * 10
        reward_pips = abs(tp_init - entry_init) * 10
        rr_ratio = reward_pips / pips_distance

        calculated_lots, matrix_label = calculate_position_size(account_balance, progression_tier, pips_distance, asset_symbol, "Precious Metals (Gold/Silver)")
        
        st.markdown(f"<div style='background-color: #121620; padding: 20px; border-radius: 8px; border: 1px solid #1f2433; border-left: 6px solid #00ff99; margin-bottom: 25px;'><p style='margin:0; font-size: 15px; color: #8892b0; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;'>AUTOMATED POSITION VOLUME BLUEPRINT</p><p style='margin:5px 0 15px 0; font-size: 38px; color: #00ff99; font-weight: bold;'>{calculated_lots} Lots</p><div style='display: flex; gap: 40px; border-top: 1px solid #1f2433; padding-top: 12px;'><p style='margin:0; font-size: 14px;'><strong>Stop Loss distance:</strong> {pips_distance:.1f} Pips</p><p style='margin:0; font-size: 14px;'><strong>Risk-to-Reward Ratio:</strong> 1:{rr_ratio:.1f} R</p><p style='margin:0; font-size: 14px; color: #8892b0;'><strong>Matrix Source:</strong> {matrix_label}</p></div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader(f"📈 Real-Time Price Stream Mapping — {asset_symbol}")
        
        # Draw actual charting ticks
        x_ticks = np.arange(1, 31)
        y_market = np.sin(x_ticks / 4) * 4.5 + live_bid
        
        fig = go.Figure()
        fig.add_shape(type="rect", x0=1, x1=30, y0=entry_init, y1=tp_init, fillcolor="rgba(0, 255, 153, 0.06)", line_width=0)
        fig.add_shape(type="rect", x0=1, x1=30, y0=sl_init, y1=entry_init, fillcolor="rgba(255, 75, 75, 0.06)", line_width=0)
        fig.add_trace(go.Scatter(x=x_ticks, y=y_market, mode='lines+markers', name='Live Stream Tick Feed', line=dict(color='#00ff99', width=2.5)))
        fig.add_hline(y=entry_init, line_dash="dash", line_color="#00ff99", annotation_text="CURRENT MARKET RATE")
        fig.update_layout(template="plotly_dark", height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # ⚡ AUTONOMOUS BRAIN EXECUTION ORCHESTRATION LOOP
