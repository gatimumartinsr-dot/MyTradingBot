import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuration setup for an elite institutional desk execution view
st.set_page_config(page_title="Kestrel — Automated Matrix Desk", layout="wide", page_icon="🦅")

# Premium Custom CSS Injection for a flawless high-contrast dark dashboard
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0b0e14 !important;
        color: #e1e4ea !important;
    }
    div[data-testid="metric-container"] {
        background-color: #121620 !important;
        border: 1px solid #1f2433 !important;
        padding: 20px !important;
        border-radius: 10px !important;
    }
    div.stAlert {
        background-color: #121620 !important;
        border: 1px solid #1f2433 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #121620 !important;
        border: 1px solid #1f2433 !important;
        border-radius: 6px 6px 0px 0px !important;
        padding: 10px 20px !important;
        color: #8892b0 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #00ff99 !important;
        border-bottom: 2px solid #00ff99 !important;
    }
</style>
""", unsafe_allow_html=True)

# Secure Session Persistence Controllers
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "active_orders" not in st.session_state:
    st.session_state.active_orders = [
        {"Ticket": "#2288104338", "Asset": "XAUUSDm", "Type": "Buy Limit", "Entry": 2500.00, "Stop": 2490.00, "Target": 2530.00, "State": "Waiting Fill"},
        {"Ticket": "#2288104112", "Asset": "XAUUSDm", "Type": "Buy Limit", "Entry": 2488.50, "Stop": 2479.00, "Target": 2516.00, "State": "Trailing"},
        {"Ticket": "#2288103907", "Asset": "EURUSDm", "Type": "Sell Limit", "Entry": 1.08650, "Stop": 1.08790, "Target": 1.08370, "State": "Breakeven"}
    ]

# Pre-seeded User Database Matrix
if "user_db" not in st.session_state:
    st.session_state.user_db = {"martins": {"password": "helix2026", "name": "Martins", "email": "martins@helix.com"}}

# --- ROUTING FRAMEWORK LOGIC ---
if not st.session_state.logged_in:
    # 🔐 PORTAL GATEWAY ENTRY SCREEN
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 50px;'>🦅 Kestrel Execution Desk</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8892b0;'>Institutional Cloud Gateway Router & Autonomous Node</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_g1, col_g2, col_g3 = st.columns([1, 1.3, 1])
    with col_g2:
        gate_mode = st.radio("Portal Interface Action", ["Sign In to Account Hub", "Register New Network Trader Profile"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if gate_mode == "Sign In to Account Hub":
            usr = st.text_input("Workspace Username Key").strip().lower()
            pwd = st.text_input("Access Password", type="password").strip()
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if usr in st.session_state.user_db and st.session_state.user_db[usr]["password"] == pwd:
                    st.session_state.logged_in = True
                    st.session_state.username = usr
                    st.rerun()
                else: st.error("Authentication Denied: Invalid credentials.")
        else:
            n_name = st.text_input("Full Trader Name")
            n_email = st.text_input("Corporate Email Anchor")
            n_user = st.text_input("Choose Username").strip().lower()
            n_pass = st.text_input("Choose Secure Password", type="password").strip()
            if st.button("Generate Workspace Credentials", type="primary", use_container_width=True):
                if n_name and n_email and n_user and n_pass:
                    st.session_state.user_db[n_user] = {"password": n_pass, "name": n_name, "email": n_email}
                    st.success("Registration Complete! Switch to Sign In to authorize access.")
                else: st.warning("Please fill out all registration fields.")
else:
    # 📈 LIVE EXECUTION WORKSPACE
    st.markdown(f"<div style='float: right; color: #8892b0;'>Broker Pipeline Status: <span style='color: #00ff99;'>● MT5 Bridge Live</span> | Operator: {st.session_state.username.upper()}</div>", unsafe_allow_html=True)
    if st.button("🔒 Sever Gateway Link", type="secondary"):
        st.session_state.logged_in = False
        st.rerun()
        
    st.title("🦅 Kestrel Execution Desk")
    st.caption("Cloud-Hosted Multi-Broker Order Routing Core Platform")
    st.markdown("---")
    
    # --- BROKER GATEWAY SIDEBAR CONTROLS ---
    st.sidebar.header("🏢 Multi-Broker Gateway")
    broker = st.sidebar.selectbox("Broker Node API", ["Exness Global", "IC Markets", "Pepperstone"])
    env_target = st.sidebar.radio("Server Production Tier", ["Demo Account Server", "Live Production Account"])
    
    b_acc = st.sidebar.number_input("Account Login ID", value=474239881, step=1)
    b_pwd = st.sidebar.text_input("Trading Execution Password", type="password", value="Pu,24ppy")
    b_srv = st.sidebar.text_input("Broker Target Server String", value="Exness-MT5-Trial15" if "Demo" in env_target else "Exness-MT5-Real1")
    
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Risk & Volume Architecture")
    rulebook = st.sidebar.selectbox("Gold Sizing Protocol", ["Conservative (1-2% Matrix)", "Medium (3-5% Balanced)", "Aggressive (8-10% High Yield)"])
    balance = st.sidebar.number_input("Account Audit Capital ($)", min_value=100.0, value=500.0, step=100.0)
    
    # --- DESK TABS SEPARATION MANAGER ---
    tab_desk, tab_journal, tab_automation = st.tabs(["🖥️ Execution Desk", "🗒️ Performance Journal", "🤖 Automation Protocols"])
    
    with tab_desk:
        # 📊 LIVE CAPITAL TRACKING BLOCKS Matrix
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("ACCOUNT BALANCE", f"${balance:,.2f}")
        m_c2.metric("CURRENT EQUITY", f"${balance + 12.60:,.2f}")
        m_c3.metric("OPEN P/L STATUS", "+$12.60", delta_color="inverse")
        m_c4.metric("RISK BUDGETED CAP", f"${balance * 0.01:,.2f}", "1.0% Allocation Base")
        
        st.markdown("---")
        
        # Core Parameters Form Grid Layout Block
        f_col1, f_col2 = st.columns([1.2, 1])
        with f_col1:
            st.subheader("⚡ Order Ticket Parameters")
            t_asset = st.text_input("Asset Instrument Symbol Suffix", value="XAUUSDm")
            t_dir = st.radio("Order Strategy Direction", ["BUY LIMIT", "SELL LIMIT"], horizontal=True)
            
            p_col1, p_col2, p_col3 = st.columns(3)
            t_entry = p_col1.number_input("Order Target Entry Price", value=2500.00, step=0.50)
            t_sl = p_col2.number_input("Stop Loss Level (Wick Edge)", value=2490.00, step=0.50)
            t_tp = p_col3.number_input("Take Profit Target Level", value=2530.00, step=0.50)
            
        with f_col2:
            st.subheader("🧮 Sizing Analytics Verification")
            pips_dist = abs(t_entry - t_sl) * 10 if "XAU" in t_asset.upper() else abs(t_entry - t_sl) * 10000
            if pips_dist == 0: pips_dist = 1.0
            
            # Fetch lot calculations mapped against data arrays matrix
            from bot import calculate_position_size
            final_lots, strategy_label = calculate_position_size(balance, rulebook, pips_dist, t_asset)
            
            reward_dist = abs(t_tp - t_entry) * 10 if "XAU" in t_asset.upper() else abs(t_tp - t_entry) * 10000
            rr_metric = reward_dist / pips_dist
            
            st.markdown(f"""
            <div style='background-color: #121620; padding: 15px; border-radius: 8px; border: 1px solid #1f2433;'>
                <p style='margin:0;'><strong>Calculated Volume Volume:</strong> <span style='color:#00ff99; font-size:18px;'>{final_lots} Lots</span></p>
                <p style='margin:5px 0 0 0;'><strong>Target Stop Width:</strong> {pips_dist:.1f} Structural Pips</p>
                <p style='margin:5px 0 0 0;'><strong>Risk to Reward Ratio Floor:</strong> 1:{rr_metric:.1f} R</p>
                <p style='margin:5px 0 0 0; color:#8892b0; font-size:12px;'>Engine Logic Source: {strategy_label}</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        
        # 📈 ORDER BLOCK VISUALIZER DRAWING RULES
        st.subheader(f"📈 Candlestick Level Visualizer Mapping — {t_asset}")
        x_axis_steps = np.arange(1, 31)
        y_sim_candles = np.sin(x_axis_steps / 4) * (t_entry * 0.003) + t_entry
        
        fig = go.Figure()
        if "BUY" in t_dir:
            fig.add_shape(type="rect", x0=1, x1=30, y0=t_entry, y1=t_tp, fillcolor="rgba(0, 255, 153, 0.08)", line_width=0)
            fig.add_shape(type="rect", x0=1, x1=30, y0=t_sl, y1=t_entry, fillcolor="rgba(255, 75, 75, 0.08)", line_width=0)
        else:
            fig.add_shape(type="rect", x0=1, x1=30, y0=t_tp, y1=t_entry, fillcolor="rgba(0, 255, 153, 0.08)", line_width=0)
            fig.add_shape(type="rect", x0=1, x1=30, y0=t_entry, y1=t_sl, fillcolor="rgba(255, 75, 75, 0.08)", line_width=0)
            
        fig.add_trace(go.Scatter(x=x_axis_steps, y=y_sim_candles, mode='lines+markers', name='Live Asset Price Stream', line=dict(color='#00ff99', width=2)))
        fig.add_hline(y=t_entry, line_dash="dash", line_color="#00ff99", annotation_text="ENTRY FOCUS LEVEL")
        fig.add_hline(y=t_sl, line_dash="dash", line_color="#ff4b4b", annotation_text="STOP PROFILE LIMIT")
        fig.add_hline(y=t_tp, line_dash="dash", line_color="#1f77b4", annotation_text="TAKE PROFIT OUTLET")
