import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from bot import calculate_position_size, dispatch_order

# Configuration setup for the institutional terminal look
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

# Global UI Style Override for Dark Premium Theme
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0d1117 !important;
    }
    div.stMetric {
        background-color: #161b22 !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border-left: 5px solid #00ff99 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize secure session states for login persistence
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# 👥 INITIALIZE EXECUTOR SYSTEM REGISTER DATABASE (Persistent during runtime)
if "user_database" not in st.session_state:
    st.session_state.user_database = {
        "martins": {"password": "helix2026", "name": "Martins", "email": "martins@helix.com", "joined": "2026-09-05 12:00"}
    }

# --- APPLICATION ROUTING LOGIC ---
if not st.session_state.logged_in:
    # 🔐 AUTHENTICATION & SIGN-UP PORTAL (LANDING SCREEN)
    st.markdown("<h1 style='text-align: center; color: #00ff99;'>🟢 HELIX OB</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888888;'>Institutional Cloud Execution Portal & Algorithmic Router</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    auth_col1, auth_col2, auth_col3 = st.columns([1, 1.4, 1])
    with auth_col2:
        gate_mode = st.radio("Choose Terminal Action", ["Sign In to Workspace", "Register New Trader Account"], horizontal=True)
        st.markdown("---")

        if gate_mode == "Sign In to Workspace":
            st.subheader("Secure Terminal Gate")
            user_input = st.text_input("Workspace Username Key").strip().lower()
            pass_input = st.text_input("Access Password", type="password").strip()
            
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if user_input in st.session_state.user_database and st.session_state.user_database[user_input]["password"] == pass_input:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.rerun()
                else:
                    st.error("Invalid Username or Password. Session Authorization Denied.")
                    
        else:
            st.subheader("📝 Trader Registration Form")
            reg_name = st.text_input("Your Full Name")
            reg_email = st.text_input("Your Email Address")
            reg_user = st.text_input("Choose Unique Username").strip().lower()
            reg_pass = st.text_input("Create Access Password", type="password").strip()
            
            if st.button("Generate Workspace Credentials", type="primary", use_container_width=True):
                if not reg_name or not reg_email or not reg_user or not reg_pass:
                    st.warning("Please fill out all identification fields to register.")
                elif reg_user in st.session_state.user_database:
                    st.error("This username is already taken. Please choose another one.")
                else:
                    st.session_state.user_database[reg_user] = {
                        "password": reg_pass,
                        "name": reg_name,
                        "email": reg_email,
                        "joined": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.success(f"🎉 Account created successfully for {reg_name}! You can now switch to 'Sign In to Workspace' above and log in.")
                    st.balloons()
else:
    # 📈 FULL PROFESSIONAL OPERATIONAL TRADING DESK
    operator_real_name = st.session_state.user_database[st.session_state.username]["name"]
    st.markdown(f"<h4 style='float: right; color: #888; margin-top:0px;'>Active Operator: <span style='color: #00ff99;'>{operator_real_name.upper()} ({st.session_state.username.upper()})</span></h4>", unsafe_allow_html=True)
    
    if st.button("🔒 Logout / Sever Connection", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
        
    st.title("🟢 Helix OB — Institutional Matrix Workspace")
    st.caption(f"Sandboxed Trading Environment Assigned to User Token: {st.session_state.username}")
    st.markdown("---")

    # --- SIDEBAR CONFIGURATION LAYER ---
    st.sidebar.header("🏢 Multi-Broker Gateway")
    broker_choice = st.sidebar.selectbox("Select Target Broker", ["Exness Global", "IC Markets", "Pepperstone", "Generic MT5 Server Gateway"])
    account_environment = st.sidebar.radio("Account Environment Target", ["Demo Account Server", "Live Production Account"], horizontal=True)
    
    broker_account = st.sidebar.number_input("Account Login ID Number", value=474239881, step=1)
    broker_password = st.sidebar.text_input("Broker Trading Password", type="password", value="SecurePass123")
    broker_server = st.sidebar.text_input("Broker Server String", value="Exness-MT5-Trial9" if "Demo" in account_environment else "Exness-MT5-Real1")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Risk Parameter Protocol")
    session_mode = st.sidebar.selectbox("Enforce Session Timing Window", ["Disable Filter", "Power Hour (Institutional Volume)", "London Open Block", "NY Session Block"])
    progression_tier = st.sidebar.selectbox("Gold Progression Tier Rulebook", ["Conservative (1-2% Matrix)", "Medium (3-5% Balanced)", "Aggressive (8-10% High Yield)"])
    account_balance = st.sidebar.number_input("Target Account Balance ($)", min_value=100.0, max_value=100000.0, value=100.0, step=100.0)

    # --- MAIN GRID ALLOCATION ---
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("⚡ Order Execution Coordinates")
        col_as1, col_as2 = st.columns(2)
        with col_as1:
            asset_symbol = st.text_input("Asset Instrument Symbol", value="XAUUSDm")
        with col_as2:
            asset_class = st.selectbox("Asset Class Tier", ["Precious Metals (Gold/Silver)", "Major Forex Pairs", "Crypto / Digital Assets"])
            
        direction = st.radio("Order Direction Matrix", ["BUY", "SELL"], horizontal=True)
        
        col_in1, col_in2, col_in3 = st.columns(3)
        with col_in1:
            entry_target = st.number_input("Order Entry Target Price", value=2500.00, step=0.10)
        with col_in2:
            sl_target = st.number_input("Stop Loss Level (Wick Edge)", value=2495.00, step=0.10)
        with col_in3:
            tp_target = st.number_input("Take Profit Target Level", value=2515.00, step=0.10)

    with col2:
        st.subheader("🧮 Algorithmic Risk Analytics")
        
        # Calculate Pips dynamically based on Asset Class Selection
        if "Precious" in asset_class or "XAU" in asset_symbol.upper() or "XAG" in asset_symbol.upper():
            pips_distance = abs(entry_target - sl_target) * 10
            reward_pips = abs(tp_target - entry_target) * 10
        elif "Forex" in asset_class:
            pips_distance = abs(entry_target - sl_target) * 10000
            reward_pips = abs(tp_target - entry_target) * 10000
        else:
            pips_distance = abs(entry_target - sl_target)
            reward_pips = abs(tp_target - entry_target)
            
        if pips_distance == 0: pips_distance = 1.0
        rr_ratio = reward_pips / pips_distance

        # Fetch lot parameters without typing mismatch bugs
        calculated_lots, matrix_label = calculate_position_size(account_balance, progression_tier, pips_distance, asset_symbol, asset_class)
        
        st.metric(label="Calculated Order Volume Blueprint", value=f"{calculated_lots} Lots")
        st.success(f"Strategy Engine Status: {matrix_label}")
        st.info(f"Target Structure Risk: {pips_distance:.1f} Pips | Risk-to-Reward Ratio: 1:{rr_ratio:.2f}")

    st.markdown("---")

    # --- DYNAMIC INTERACTIVE MULTI-TAB WORKSPACE ---
    if st.session_state.username == "martins":
        tab1, tab2, tab3, tab4 = st.tabs(["📉 Institutional Charts", "📋 Strategy Rulebook Protocols", "🗒 Active Live Trade Journal", "🔒 EXECUTIVE USER ACCESS REGISTRY PANEL"])
    else:
        tab1, tab2, tab3 = st.tabs(["📉 Institutional Charts", "📋 Strategy Rulebook Protocols", "🗒 Active Live Trade Journal"])
        tab4 = None

    with tab1:
        st.subheader("📊 Interactive Order Block Visualizer Mapping")
        position_type = "Long Position" if direction == "BUY" else "Short Position"
        st.caption(f"Visualizing Projection Coordinates for an automated **{direction} ({position_type})** sequence on **{asset_symbol}**")
        
        x_ticks = np.arange(1, 26)
        y_market = np.sin(x_ticks / 3) * (entry_target * 0.002) + entry_target
        fig = go.Figure()
        
        if direction == "BUY":
            fig.add_shape(type="rect", x0=1, x1=25, y0=entry_target, y1=tp_target, fillcolor="rgba(0, 255, 153, 0.15)", line_width=0)
            fig.add_shape(type="rect", x0=1, x1=25, y0=sl_target, y1=entry_target, fillcolor="rgba(255, 75, 75, 0.15)", line_width=0)
        else:
            fig.add_shape(type="rect", x0=1, x1=25, y0=tp_target, y1=entry_target, fillcolor="rgba(0, 255, 153, 0.15)", line_width=0)
            fig.add_shape(type="rect", x0=1, x1=25, y0=entry_target, y1=sl_target, fillcolor="rgba(255, 75, 75, 0.15)", line_width=0)
            
        fig.add_trace(go.Scatter(x=x_ticks, y=y_market, mode='lines', name='Live Asset Price Feed', line=dict(color='#888888', width=1.5)))
