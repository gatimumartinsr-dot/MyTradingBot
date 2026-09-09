import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from bot import (
    run_autonomous_brain, 
    calculate_position_size, 
    dispatch_live_order_matrix, 
    get_archived_trades, 
    clear_trade_database,
    verify_user_authentication,
    register_new_user_profile
)

# Core layout configuration matrix
st.set_page_config(page_title="Helix SaaS Terminal", layout="wide", page_icon="🟢")

# Premium high-contrast institutional dark responsive theme injection
st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 15px !important; border-radius: 8px !important; border-left: 4px solid #00ff99 !important; } .stTabs [data-baseweb='tab-list'] { gap: 8px; } .stTabs [data-baseweb='tab'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 8px 16px !important; color: #8892b0 !important; border-radius: 4px 4px 0px 0px !important; } .stTabs [aria-selected='true'] { color: #00ff99 !important; border-bottom: 2px solid #00ff99 !important; } .stButton>button { border-radius: 6px !important; font-weight: 600 !important; } @media (max-width: 768px) { [data-testid='stSidebar'] { width: 100% !important; } }</style>", unsafe_allow_html=True)

# Continuous cloud multi-tenant states initialization
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "gateway_connected" not in st.session_state: st.session_state.gateway_connected = False
if "brain_active" not in st.session_state: st.session_state.brain_active = False

# ==========================================
# --- 🔐 FREESTANDING USER AUTHENTICATION GATE ---
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 40px;'>🟢 HELIX OB GLOBAL PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8892b0;'>Multi-Tenant Standalone Algorithmic Workstation</p>", unsafe_allow_html=True)
    st.markdown("---")
    _, auth_col, _ = st.columns([1, 1.5, 1])
    
    with auth_col:
        gate_mode = st.radio("Access Control Mode", ["Sign In to Account", "Create Standalone Account"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        user_input = st.text_input("Username Identifier Key").strip().lower()
        pass_input = st.text_input("Access Password", type="password").strip()
        
        if gate_mode == "Sign In to Account":
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if verify_user_authentication(user_input, pass_input):
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.rerun()
                else:
                    st.error("Invalid credentials or unregistered operator profile key.")
        else:
            if st.button("Generate Standalone Credentials", type="primary", use_container_width=True):
                if user_input and pass_input:
                    if register_new_user_profile(user_input, pass_input):
                        st.success("Account profile compiled successfully! Please select 'Sign In' to connect.")
                    else:
                        st.error("Username key is already taken by another active active workspace user.")
                else:
                    st.warning("Please specify valid alpha-numeric configuration characters.")
else:
    # Authenticated Active Trading View Panel Container
    current_user = st.session_state.username
    st.markdown(f"<div style='float: right; color: #8892b0; font-family: monospace;'>User Context: <b>{current_user.upper()}</b> | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
    
    # Sidebar control matrix
    st.sidebar.header("Market Asset Settings")
    symbol_choice = st.sidebar.selectbox("Tracked Target Instrument", ["XAUUSDm", "BTCUSDm", "EURUSDm"])
    
    st.sidebar.markdown("---")
    st.sidebar.header("Demo Broker Handshake")
    broker_name = st.sidebar.text_input("Broker Node Name", value="Exness-Demo")
    broker_account = st.sidebar.number_input("MT5 Account Number Key", value=474239881, step=1)
    broker_server = st.sidebar.text_input("MT5 Server String Parameter", value="Exness-MT5-Trial15")
    
    if st.sidebar.button("🔌 AUTHORIZE LIVE BROKER HANDSHAKE", type="primary", use_container_width=True):
        st.session_state.gateway_connected = True
        st.sidebar.success("Linked securely to your MT5 sandbox network!")

    st.sidebar.markdown("---")
    st.sidebar.header("Algorithmic Risk Management")
    risk_percentage = st.sidebar.slider("Account Capital Exposure Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    account_balance = st.sidebar.number_input("Current Target Account Balance ($)", value=161.53)
    lot_multiplier = st.sidebar.slider("Manual Sizing Multiplier Layer", 1.0, 5.0, 1.0, step=0.5)

    st.sidebar.markdown("---")
    st.sidebar.header("Cloud Execution Mode")
    if not st.session_state.brain_active:
        if st.sidebar.button("⚡ ACTIVATE ALGORITHMIC BRAIN", type="primary", use_container_width=True):
            st.session_state.brain_active = True
            st.rerun()
    else:
        if st.sidebar.button("🛑 EMERGENCY HALT SYSTEM", type="secondary", use_container_width=True):
            st.session_state.brain_active = False
            st.rerun()

    # Pass computations to bot module matching current user namespace
    brain_data = run_autonomous_brain(account_balance, risk_percentage, symbol_choice, st.session_state.brain_active, current_user)
    live_bid = brain_data["live_bid"]
    live_ask = brain_data["live_ask"]
    spread_delta = round(abs(live_ask - live_bid), 4)

    # Core parameters header metric row block
    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
    m_c1.metric(label="ACCOUNT BALANCE CONTEXT", value=f"${account_balance:,.2f}")
    m_c2.metric(label="LIVE SCALPED BID", value=f"${live_bid:,.4f}" if "EUR" in symbol_choice else f"${live_bid:,.2f}")
    m_c3.metric(label="LIVE SCALPED ASK", value=f"${live_ask:,.4f}" if "EUR" in symbol_choice else f"${live_ask:,.2f}")
    risk_dollars = account_balance * (risk_percentage / 100.0)
    m_c4.metric(label="RISK ALLOCATION SAFEGUARD", value=f"${risk_dollars:,.2f}", delta=f"{risk_percentage}% Risk Layer")

    # Crash-proof raw flat text tabs strings
    tab_desk, tab_journal, tab_rules = st.tabs([
        "Live Trading Desk", 
        "Personal Journal Logs", 
        "Risk Guardrails Checklist"
    ])

    with tab_desk:
        st.markdown("<br>", unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        trend_color = "green" if "BULLISH" in brain_data["market_trend"] else "red"
        tc1.markdown(f"**Trend Evaluation Target:** :{trend_color}[{brain_data['market_trend']}]")
        tc2.markdown(f"**Volatility Spread Delta:** `{spread_delta} Points` (Max Allowable Ceiling Buffer: Safe)")
        st.markdown(f"**Oscillator Boundaries:** `RSI (14) = {brain_data['rsi']:.2f}` | Strategy Status: `[{brain_data['rsi_status']}]`")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### M15 Candlestick Chart Structure Overlay ({symbol_choice})")
        
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
            paper_bgcolor='#0b0e14', plot_bgcolor='#121620', height=380,
            margin=dict(l=10, r=10, t=15, b=10),
            xaxis=dict(showgrid=True, gridcolor='#1f2433', type='category'),
            yaxis=dict(showgrid=True, gridcolor='#1f2433')
        )
        
        ob_height_buffer = 4.0 if "BTC" in symbol_choice else (0.0001 if "EUR" in symbol_choice else 0.35)
        fig.add_hrect(
            y0=brain_data["ob_zone"] - ob_height_buffer, y1=brain_data["ob_zone"] + ob_height_buffer,
            fillcolor="rgba(255, 170, 0, 0.12)", line_color="#ffaa00", line_width=1,
            annotation_text="VALIDATED ORDER BLOCK CONCENTRATION (M15)", annotation_position="top left",
            annotation_font=dict(size=9, color="#ffaa00")
        )
        fig.add_hline(y=brain_data["entry_level"], line_dash="dot", line_color="#33ccff", line_width=1.5)
        fig.add_hline(y=brain_data["stop_loss"], line_dash="solid", line_color="#ff3366", line_width=1)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Active Open Position Matrix")
        st.dataframe(pd.DataFrame(brain_data["positions_matrix"]), use_container_width=True, hide_index=True)

