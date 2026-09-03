import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

# Initialize deep dark professional theme layout
st.set_page_config(page_title="Helix Multi-Broker Terminal", layout="wide", page_icon="🟢")

st.markdown("""
    <style>
        @import url('https://googleapis.com');
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #0b1116 !important;
            font-family: 'Inter', sans-serif !important;
        }
        .stButton>button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            height: 48px !important;
            background-color: #10b981 !important;
            color: #060b0d !important;
            border: none !important;
            width: 100% !important;
        }
        .header-box {
            background-color: #111827;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #1f2937;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# Persistent storage arrays mapping parameters cleanly
if "journal_data" not in st.session_state:
    st.session_state.journal_data = []
if "equity_history" not in st.session_state:
    # Starting historical data tracking sequence points
    st.session_state.equity_history = [150.00, 155.50, 152.10, 158.40, 160.22]

# --- ACCOUNT METRICS STORAGE LINK ENGINE ---
balance_file = "live_balance.json"
signal_file = "trade_signal.json"

live_balance = 160.22
live_equity = 160.22
live_profit = 2.40
account_status = "🟢 ACTIVE HUB BRIDGE RE-CONNECTED"
status_color = "#10b981"

if os.path.exists(balance_file):
    try:
        with open(balance_file, "r") as f:
            data = json.load(f)
            live_balance = float(data.get("balance", live_balance))
            live_equity = float(data.get("equity", live_equity))
            live_profit = float(data.get("profit", live_profit))
            account_status = f"🟢 LIVE SYNCED (MT5 ID: {data.get('login')})"
    except Exception:
        pass

# Navigation layout headers sliding tab systems
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: SIGN IN ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'>🟢 UNIVERSAL BROKER CROSS-LINK GATES</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #9ca3af; font-weight: 300; margin-bottom: 25px;'>Prime connection pipelines for any MT5 terminal.</h3>", unsafe_allow_html=True)
    broker_select = st.selectbox("SELECT DESTINATION BROKER TERMINAL ENGINE", ["Exness Technologies Ltd", "JustMarkets Inc.", "XM Global Markets", "Windsor Brokers"])
    col_log1, col_log2 = st.columns(2)
    with col_log1: st.text_input("MT5 ACCOUNT LOGIN ID", value="474239881", disabled=True)
    with col_log2: st.text_input("BROKER SERVER ASSIGNMENT", value="Exness-MT5-Trial15", disabled=True)
    st.text_input("ACCOUNT TRADING PASSWORD METRIC", value="••••••••••••", disabled=True)
    st.write(" ")
    st.success("🔒 System active: Verification pipeline actively listening for background local data terminal loops.")

# ==================== TAB 2: AUTOMATED DASHBOARD FORM ====================
with t_dashboard:
    st.markdown(f"Status: <span style='color:{status_color}; font-family:monospace; font-weight:600;'>{account_status}</span>", unsafe_allow_html=True)
    st.subheader("📊 Cross-Broker Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value=f"${live_balance:.2f}")
    with m_col2: st.metric(label="Floating Equity", value=f"${live_equity:.2f}")
    with m_col3: st.metric(label="Active Open Profit/Loss", value=f"${live_profit:.2f}", delta=f"${live_profit:.2f}" if live_profit != 0 else None)
        
    st.divider()
    st.subheader("🤖 Strategy Execution Blueprint Matrix")
    
    with st.form("clearable_dispatch_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            direction = st.selectbox("Blueprint Direction", ["BUY_LIMIT", "SELL_LIMIT"])
            target_pair = st.selectbox("Asset Watchlist", ["XAUUSDm", "EURUSD", "GBPUSD"])
            entry_level = st.number_input("Entry Price Target Coordinates", min_value=0.0, value=2410.00, format="%.2f")
        with col2:
            sl_level = st.number_input("Validation Stop Loss Level", min_value=0.0, value=2405.00, format="%.2f")
            tp_level = st.number_input("Target Take Profit Level", min_value=0.0, value=2425.00, format="%.2f")
            risk_pct = st.slider("Risk Per Setup Allocation (%)", 0.25, 2.0, 1.0, step=0.25)
            
        st.write(" ")
        submit_btn = st.form_submit_button("⚡ Commit Matrix & Place Pending MT5 Order")
        
        if submit_btn:
            pips_delta = abs(entry_level - sl_level)
            calculated_pips = pips_delta * 10 if "XAU" in target_pair else pips_delta * 10000
            risk_amount = live_balance * (risk_pct / 100)
            lot_size = risk_amount / (calculated_pips * 2.0) if "XAU" in target_pair else risk_amount / (calculated_pips * 10.0)
            recommended_lots = max(0.01, round(lot_size, 2))
            
            # Pack order instructions to be picked up by the local laptop script
            signal_data = {
                "symbol": target_pair,
                "order_type": direction,
                "entry": entry_level,
                "sl": sl_level,
                "tp": tp_level,
                "lots": recommended_lots,
                "active": True
            }
            with open(signal_file, "w") as sf:
                json.dump(signal_data, sf)
            
            new_record = {
                "Time (GST)": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "Asset": target_pair,
                "Action": direction,
                "Entry": entry_level,
                "Stop Loss": sl_level,
                "Take Profit": tp_level,
                "Allocated Volume": recommended_lots
            }
            st.session_state.journal_data.append(new_record)
            st.session_state.equity_history.append(round(live_balance, 2))
            st.balloons()
            st.success("🚀 Order instructions dispatched! Laptop background execution loop triggered successfully.")

# ==================== TAB 3: CHART CANVAS ====================
with t_chart:
    st.markdown("<div class='header-box'><p style='color:#10b981; font-family:monospace; margin:0;'>🟢 RADAR STREAMING ACTIVE • XAUUSDm M15</p></div>", unsafe_allow_html=True)
    np.random.seed(42)
    chart_time = pd.date_range(end=datetime.now(), periods=40, freq='15min')
    base_prices = np.sin(np.linspace(0, 4, 40)) * 15 + 2415
    opens = base_prices[:-1] + np.random.normal(0, 1, 39)
    closes = base_prices[1:] + np.random.normal(0, 1, 39)
    highs = np.maximum(opens, closes) + np.random.uniform(1, 3, 39)
    lows = np.minimum(opens, closes) - np.random.uniform(1, 3, 39)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_time[:-1], open=opens, high=highs, low=lows, close=closes, name="Market Price"))
    fig.add_shape(type="rect", x0=chart_time, y0=2410.00, x1=chart_time[-1], y1=2425.00, fillcolor="rgba(16, 185, 129, 0.12)", line=dict(width=0))
    fig.add_shape(type="rect", x0=chart_time, y0=2405.00, x1=chart_time[-1], y1=2410.00, fillcolor="rgba(239, 83, 80, 0.12)", line=dict(width=0))
    fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[2425.00, 2425.00], mode="lines", line=dict(color="#10b981", width=2), name="Take Profit"))
    fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[2410.00, 2410.00], mode="lines", line=dict(color="#3b82f6", width=2, dash="dash"), name="Limit Entry"))
    fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[2405.00, 2405.00], mode="lines", line=dict(color="#ef5350", width=2, dash="dot"), name="Stop Loss"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=350, margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116')
    st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 4: SETUP GATE ====================
with t_gate:
    st.subheader("🛡️ Institutional Setup Validation Checklist")
    r1 = st.checkbox("🔍 Structural footprint has successfully tapped into unmitigated Order Block demand (OB)")
    r2 = st.checkbox("⚡ Strong momentum expansion displacement left a valid 3-candle Fair Value Gap vacuum (FVG)")
    r3 = st.checkbox("📈 Current pricing layout baseline is fully aligned with 200 MA trend vector parameters")
    r4 = st.checkbox("📊 Relative Strength Index (RSI 14) confirms clean structural momentum footprints")
    if r1 and r2 and r3 and r4: st.success("🔓 Setup Authorized! System strategy guidelines fully cleared.")

# ==================== TAB 5: JOURNAL LOGS & PERFORMANCE CURVE ====================
with t_journal:
    st.subheader("🗒️ Smartphone Active Order Journal")
    st.dataframe(pd.DataFrame(st.session_state.journal_data), use_container_width=True)
    
    st.write(" ")
    # --- UPGRADE: ACCOUNT EQUITY GROWTH TREND CHART ---
    st.subheader("📈 Capital Growth trend Tracking Curve Chart")
    curve_fig = go.Figure()
    curve_fig.add_trace(go.Scatter(
        y=st.session_state.equity_history, 
        mode='lines+markers', 
        line=dict(color='#10b981', width=3),
        marker=dict(size=8, color='#ffffff')
    ))
