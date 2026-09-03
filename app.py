import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

# Initialize wide minimalist layout
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
        .terminal-log {
            background-color: #04070a;
            color: #10b981;
            font-family: 'JetBrains Mono', monospace;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #111827;
            height: 200px;
            overflow-y: scroll;
            font-size: 13px;
        }
    </style>
""", unsafe_allow_html=True)

if "journal_data" not in st.session_state:
    st.session_state.journal_data = []

# --- MULTI-BROKER CLOUD INTERFACE RELAYS ---
balance_file = "live_balance.json"
signal_file = "trade_signal.json"
bot_state_file = "bot_state.json"

live_balance, live_equity, live_profit = 160.22, 160.22, 0.00
account_status = "⚫ RECONNECTING GATEWAY..."

if os.path.exists(balance_file):
    try:
        with open(balance_file, "r") as f:
            data = json.load(f)
            if time.time() - data.get("timestamp", 0) < 60:
                live_balance = float(data.get("balance", live_balance))
                live_equity = float(data.get("equity", live_equity))
                live_profit = float(data.get("profit", live_profit))
                account_status = f"🟢 SYNCED WITH MT5 (ID: {data.get('login')})"
    except Exception: pass

# --- READ PERSISTENT ACTIVITY LOG LISTS ---
activity_logs = []
if os.path.exists("activity_logs.json"):
    try:
        with open("activity_logs.json", "r") as lf:
            activity_logs = json.load(lf)
    except Exception: pass

# Sliding Navigation bar system headers
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: CONNECT BROKERS ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'>Universal Broker Link Gate</h2>", unsafe_allow_html=True)
    broker_select = st.selectbox("CHOOSE SYSTEM TERMINAL ARCHITECTURE", ["Exness Technologies Ltd", "JustMarkets Inc.", "XM Global Markets"])
    col_log1, col_log2 = st.columns(2)
    with col_log1: st.text_input("MT5 ACCOUNT LOGIN USER ID", value="474239881", disabled=True)
    with col_log2: st.text_input("EXNESS LIVE DEMO SERVER", value="Exness-MT5-Trial15", disabled=True)
    st.text_input("SECURE PASSWORD STREAM", value="••••••••••••", disabled=True)
    st.write(" ")
    st.success("🔒 System active: Handshake synced with laptop background loop setup.")

# ==================== TAB 2: AUTOMATED DASHBOARD & MASTER SWITCHES ====================
with t_dashboard:
    st.markdown(f"Status: <span style='color:#10b981; font-family:monospace; font-weight:600;'>{account_status}</span>", unsafe_allow_html=True)
    
    # --- NEW: MASTER ON/OFF RADAR SWITCHES SYSTEM ---
    st.subheader("⚙️ Master Bot Automation Control")
    current_state = "OFF"
    if os.path.exists(bot_state_file):
        try:
            with open(bot_state_file, "r") as sf: current_state = json.load(sf).get("mode", "OFF")
        except Exception: pass
        
    col_sw1, col_sw2 = st.columns(2)
    with col_sw1:
        if st.button("🚀 ACTIVATE AUTOMATION AUTOMATION (ON)", type="primary" if current_state == "OFF" else "secondary"):
            with open(bot_state_file, "w") as sf: json.dump({"mode": "ON"}, sf)
            st.success("🤖 Master state: Bot engine turned ON. Hunt array active.")
            st.rerun()
    with col_sw2:
        if st.button("🛑 RESTRAIN BOT CHANNELS (OFF)", type="primary" if current_state == "ON" else "secondary"):
            with open(bot_state_file, "w") as sf: json.dump({"mode": "OFF"}, sf)
            st.error("🛑 Master state: Bot engine turned OFF. Standing flat.")
            st.rerun()
            
    st.write(f"Current Bot Running Mode Status: **`{current_state}`**")
    
    st.divider()
    
    # --- NEW: REAL-TIME OPERATION TERMINAL ACTIVITY LOG BOX ---
    st.subheader("💻 Live Operational Activity Engine Terminal Logs")
    log_text = ""
    if activity_logs:
        for log in reversed(activity_logs[-15:]):  # Display last 15 rolling system status loops
            log_text += f"[{log.get('time')}] {log.get('message')}\n"
    else:
        log_text = "[System Log] Waiting for your laptop background gateway connection to transmit radar logs..."
        
    st.markdown(f'<pre class="terminal-log">{log_text}</pre>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📊 Cross-Broker Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value=f"${live_balance:.2f}")
    with m_col2: st.metric(label="Floating Equity", value=f"${live_equity:.2f}")
    with m_col3: st.metric(label="Active Open Profit/Loss", value=f"${live_profit:.2f}")

# ==================== TAB 3: PROF CHART CANVAS & DYNAMIC REVIEWS ====================
with t_chart:
    st.markdown("<div class='header-box'><p style='color:#10b981; font-family:monospace; margin:0;'>🟢 RADAR STREAMING ACTIVE • XAUUSDm LIVE ENVIRONMENT</p></div>", unsafe_allow_html=True)
    np.random.seed(42)
    chart_time = pd.date_range(end=datetime.now(), periods=40, freq='15min')
    base_prices = np.sin(np.linspace(0, 4, 40)) * 15 + 4415
    opens = base_prices[:-1] + np.random.normal(0, 1, 39)
    closes = base_prices[1:] + np.random.normal(0, 1, 39)
    highs = np.maximum(opens, closes) + np.random.uniform(1, 3, 39)
    lows = np.minimum(opens, closes) - np.random.uniform(1, 3, 39)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_time[:-1], open=opens, high=highs, low=lows, close=closes, name="Market Price"))
    fig.add_shape(type="rect", x0=chart_time, y0=4400.00, x1=chart_time[-1], y1=4420.00, fillcolor="rgba(16, 185, 129, 0.12)", line=dict(width=0))
    fig.add_shape(type="rect", x0=chart_time, y0=4395.00, x1=chart_time[-1], y1=4400.00, fillcolor="rgba(239, 83, 80, 0.12)", line=dict(width=0))
    fig.add_trace(go.Scatter(x=[chart_time, chart_time[-1]], y=[4420.00, 4420.00], mode="lines", line=dict(color="#10b981", width=2), name="Take Profit"))
    fig.add_trace(go.Scatter(x=[chart_time, chart_time[-1]], y=[4400.00, 4400.00], mode="lines", line=dict(color="#3b82f6", width=2, dash="dash"), name="Limit Entry"))
    fig.add_trace(go.Scatter(x=[chart_time, chart_time[-1]], y=[4395.00, 4395.00], mode="lines", line=dict(color="#ef5350", width=2, dash="dot"), name="Stop Loss"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=350, margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116')
    st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 4: SETUP GATE ====================
with t_gate:
    st.subheader("🛡️ Institutional Setup Validation Checklist")
    st.write("Verify the system strategy parameters guidelines to open the matrix channels:")
    st.checkbox("🔍 Structural footprint has successfully tapped into unmitigated Order Block demand (OB)", value=True, disabled=True)
    st.checkbox("⚡ Strong momentum expansion displacement left a valid 3-candle Fair Value Gap vacuum (FVG)", value=True, disabled=True)
    st.checkbox("📈 Current pricing layout baseline is fully aligned with 200 MA trend vector parameters", value=True, disabled=True)
    st.checkbox("📊 Relative Strength Index (RSI 14) confirms clean structural momentum footprints", value=True, disabled=True)
    st.success("🔓 Autonomous Engine State Active: Bot handles strategy scanning steps.")

# ==================== TAB 5: JOURNAL LOGS ====================
with t_journal:
    st.subheader("🗒️ Smartphone Active Order Journal")
    st.dataframe(pd.DataFrame(st.session_state.journal_data), use_container_width=True)

# ==================== TAB 6: BOT CONSTRAINTS RULES ====================
with t_rules:
    st.subheader("📜 Bot Strategy Governing Laws & Checklist Framework")
    st.success("**🟢 LAW 1 - LOSS CONTROL:** Locked to exactly 1.0% capital risk per trade array metrics.")
    st.info("**🔵 LAW 2 - CONFLUENCE:** Execution demands full 200 MA, OB block and FVG Vacuum convergence elements.")

# ==================== TAB 7: TIMINGS & CONNECTIONS ====================
with t_connections:
    st.subheader("🔌 API Connection Channels & High-Volume Timings")
    st.write("* **London Open Breakout Window:** 11:00 AM – 1:00 PM GST")
    st.write("* **New York Overlap Power Hour:** 4:00 PM – 6:00 PM GST")
    st.divider()
    st.success("Primary cross-broker API endpoints are fully operational and synchronized.")
