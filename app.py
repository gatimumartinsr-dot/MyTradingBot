 import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

# Force premium dark theme layout configurations
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

st.markdown("""
    <style>
        @import url('https://googleapis.com');
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #0d1117 !important;
            font-family: 'Inter', sans-serif !important;
        }
        .stButton>button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            height: 52px !important;
            font-size: 16px !important;
        }
        .btn-setup>button {
            background-color: #10b981 !important;
            color: #0b1117 !important;
            border: none !important;
        }
        .btn-flatten>button {
            background-color: #261619 !important;
            color: #f87171 !important;
            border: 1px solid #7f1d1d !important;
        }
        .meta-label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #4b5563;
            text-transform: uppercase;
        }
        .meta-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #e5e7eb;
            text-align: right;
        }
        .analysis-card {
            background-color: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .pill-indicator {
            background-color: #1f2937;
            color: #9ca3af;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
        }
    </style>
""", unsafe_allow_html=True)

if "journal_data" not in st.session_state:
    st.session_state.journal_data = []

# --- RELAY DATA PIPELINE CONFIGURATION SETTINGS ---
balance_file = "live_balance.json"
bot_state_file = "bot_state.json"
activity_logs = []

live_balance, live_equity, live_profit = 160.22, 160.22, 0.00
current_bot_mode = "OFF"

if os.path.exists(balance_file):
    try:
        with open(balance_file, "r") as f:
            d = json.load(f)
            if time.time() - d.get("timestamp", 0) < 60:
                live_balance = float(d.get("balance", live_balance))
                live_equity = float(d.get("equity", live_equity))
                live_profit = float(data.get("profit", live_profit))
    except Exception: pass

if os.path.exists(bot_state_file):
    try:
        with open(bot_state_file, "r") as f: current_bot_mode = json.load(f).get("mode", "OFF")
    except Exception: pass

if os.path.exists("activity_logs.json"):
    try:
        with open("activity_logs.json", "r") as f: activity_logs = json.load(f)
    except Exception: pass

# --- FIXED: GENERATED EXPLICITLY INDEPENDENT SLIDING TABS ARRAYS ---
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: SIGN IN ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'>Universal Broker Link Gate</h2>", unsafe_allow_html=True)
    broker_select = st.selectbox("CHOOSE SYSTEM TERMINAL ARCHITECTURE", ["Exness Technologies Ltd", "JustMarkets Inc.", "XM Global Markets"])
    col_log1, col_log2 = st.columns(2)
    with col_log1: st.text_input("MT5 ACCOUNT LOGIN USER ID", value="474239881", disabled=True)
    with col_log2: st.text_input("EXNESS LIVE DEMO SERVER", value="Exness-MT5-Trial15", disabled=True)
    st.text_input("SECURE PASSWORD STREAM", value="••••••••••••", disabled=True)
    st.write(" ")
    st.success("🔒 System active: Handshake synced with laptop background loop setup.")

# ==================== TAB 2: RESTORED DASHBOARD / AUTONOMOUS MASTER CONTROLS ====================
with t_dashboard:
    st.subheader("📊 Cross-Broker Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value=f"${live_balance:.2f}")
    with m_col2: st.metric(label="Floating Equity", value=f"${live_equity:.2f}")
    with m_col3: st.metric(label="Active Open Profit/Loss", value=f"${live_profit:.2f}")
        
    st.divider()
    st.subheader("⚙️ Master Bot Automation Control Switch")
    
    col_on, col_off = st.columns(2)
    with col_on:
        if st.button("🚀 ACTIVATE AUTOMATION BOT (ON)", use_container_width=True, key="dashboard_on_btn"):
            with open(bot_state_file, "w") as sf: json.dump({"mode": "ON"}, sf)
            st.rerun()
    with col_off:
        if st.button("🛑 DISABLE AUTOMATION RESTRAIN (OFF)", use_container_width=True, key="dashboard_off_btn"):
            with open(bot_state_file, "w") as sf: json.dump({"mode": "OFF"}, sf)
            st.rerun()
            
    st.write(f"Current Bot System Operational Mode: **`{current_bot_mode}`**")
    st.divider()
    
    st.subheader("💻 Live Operational Activity Engine Terminal Logs")
    log_txt = ""
    if activity_logs:
        for entry in reversed(activity_logs[-10:]):
            log_txt += f"[{entry.get('time')}] {entry.get('message')}\n"
    else:
        log_txt = "[System] Waiting for laptop gateway.py terminal link to sync active tracking log entries..."
    st.code(log_txt, language="bash")

# ==================== TAB 3: CHART & ELITE ANALYTICAL CARDS ====================
with t_chart:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("<h3 style='margin:0; padding:0; color:white; font-weight:600;'>XAUUSD <span style='font-size:12px; color:#4b5563; font-family:monospace;'>EXNESS M15</span></h3>", unsafe_allow_html=True)
        st.markdown("<h2 style='margin:0; padding:0; color:white; font-family:monospace; font-weight:700;'>3,408.60 <span style='font-size:15px; color:#10b981; font-weight:500;'>+0.38%</span></h2>", unsafe_allow_html=True)
    with col_s2:
        st.markdown("<p style='text-align:right; font-family:monospace; margin:0;'><span class='pill-indicator'>🟢 16:10 GST</span>&nbsp;&nbsp;<span class='pill-indicator' style='color:#60a5fa;'>DEMO ACCOUNT</span></p>", unsafe_allow_html=True)

    st.write(" ")
    st.markdown("<span style='color:#fbbf24; font-family:monospace; font-size:13px; font-weight:500;'>-- POWER HOUR 16:00-18:00 GST</span>", unsafe_allow_html=True)
    st.markdown("<p style='color:#10b981; font-family:monospace; font-size:12px; margin-top:2px;'>BOS CONFIRMED • FVG VACUUM UNMITIGATED</p>", unsafe_allow_html=True)

    np.random.seed(42)
    t_bars = pd.date_range(end=datetime.now(), periods=45, freq='15min')
    prices = np.sin(np.linspace(0, 4.5, 45)) * 18 + 3402
    opens = prices[:-1] + np.random.normal(0, 1.2, 44)
    closes = prices[1:] + np.random.normal(0, 1.2, 44)
    highs = np.maximum(opens, closes) + np.random.uniform(0.5, 3.5, 44)
    lows = np.minimum(opens, closes) - np.random.uniform(0.5, 3.5, 44)

    fig = go.Figure(data=[go.Candlestick(
        x=t_bars[:-1], open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#10b981', decreasing_line_color='#ef5350',
        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef5350'
    )])

    fig.add_shape(type="rect", x0=t_bars, y0=3412.00, x1=t_bars[-1], y1=3421.10, fillcolor="rgba(96, 165, 250, 0.08)", line=dict(width=0))
    fig.add_shape(type="rect", x0=t_bars, y0=3392.00, x1=t_bars[-1], y1=3402.00, fillcolor="rgba(59, 130, 246, 0.15)", line=dict(width=0))

    fig.add_trace(go.Scatter(x=[t_bars, t_bars[-1]], y=[3412.00, 3412.00], mode="lines", line=dict(color="#60a5fa", width=1.5, dash="dash"), name="FVG Open"))
    fig.add_trace(go.Scatter(x=[t_bars, t_bars[-1]], y=[3402.00, 3402.00], mode="lines", line=dict(color="#10b981", width=1.5), name="Entry Limit"))
    fig.add_trace(go.Scatter(x=[t_bars, t_bars[-1]], y=[3392.00, 3392.00], mode="lines", line=dict(color="#ef5350", width=1.5, dash="dot"), name="Invalidation SL"))

    fig.update_layout(
        template="plotly_dark", xaxis_rangeslider_visible=False, height=360,
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#21262d', side="right")
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.write(" ")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.markdown('<div class="btn-setup">', unsafe_allow_html=True)
        st.button("Review setup", key="review_panel_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with btn_col2:
        st.markdown('<div class="btn-flatten">', unsafe_allow_html=True)
        st.button("Flatten all", key="flatten_panel_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.write(" ")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("""
            <table style='width:100%; border:none; border-collapse:collapse;'>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>ENGINE</td><td class='meta-value' style='color:#10b981;'>AUTONOMOUS ACTIVE</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>MODELS</td><td class='meta-value'>A:OrderBlock Demand B:FVG-Retest</td></tr>
            </table>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
            <table style='width:100%; border:none; border-collapse:collapse;'>
