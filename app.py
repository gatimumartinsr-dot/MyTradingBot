import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

# Force an ultra-premium deep minimalist dark background theme configuration 
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

# Custom UI overrides to inject the exact professional color accents from your reference photo
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

# Instantiating session tracking matrices
if "journal_data" not in st.session_state:
    st.session_state.journal_data = []

# Core account relay configuration states loading profiles
balance_file = "live_balance.json"
bot_state_file = "bot_state.json"
activity_logs = []

live_balance, live_equity, live_profit = 160.22, 160.22, 0.00
current_bot_mode = "OFF"

# Sync parameters directly from your laptop background processes
if os.path.exists(balance_file):
    try:
        with open(balance_file, "r") as f:
            d = json.load(f)
            if time.time() - d.get("timestamp", 0) < 60:
                live_balance = float(d.get("balance", live_balance))
                live_equity = float(d.get("equity", live_equity))
                live_profit = float(d.get("profit", live_profit))
    except Exception: pass

if os.path.exists(bot_state_file):
    try:
        with open(bot_state_file, "r") as f: current_bot_mode = json.load(f).get("mode", "OFF")
    except Exception: pass

if os.path.exists("activity_logs.json"):
    try:
        with open("activity_logs.json", "r") as f: activity_logs = json.load(f)
    except Exception: pass

# --- FIXED LINKED BOTTOM SYSTEM NAVIGATION CORES ---
t_chart, t_dashboard, t_journal, t_rules = st.tabs([
    "📈 REAL-TIME CHART", "🎛️ CONTROL PANEL", "🗒️ HISTORICAL JOURNAL", "📜 GOVERNING LAWS"
])

# ==================== TAB 1: ELITE SPECIFICATION CHART & LEDGER ANALYSIS ====================
with t_chart:
    # Top Section Status Bar Row Components
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("<h3 style='margin:0; padding:0; color:white; font-weight:600;'>XAUUSD <span style='font-size:12px; color:#4b5563; font-family:monospace;'>EXNESS M15</span></h3>", unsafe_allow_html=True)
        st.markdown("<h2 style='margin:0; padding:0; color:white; font-family:monospace; font-weight:700;'>3,408.60 <span style='font-size:15px; color:#10b981; font-weight:500;'>+0.38%</span></h2>", unsafe_allow_html=True)
    with col_s2:
        st.markdown("<p style='text-align:right; font-family:monospace; margin:0;'><span class='pill-indicator'>🟢 16:10 GST</span>&nbsp;&nbsp;<span class='pill-indicator' style='color:#60a5fa;'>DEMO ACCOUNT</span></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:right; font-family:monospace; margin-top:5px; font-size:12px; color:#9ca3af;'>ENGINE ENGINE STATE: <span style='color:#10b981; font-weight:bold;'>{current_bot_mode}</span></p>", unsafe_allow_html=True)

    # Strategy Status Overlay Text Lines
    st.write(" ")
    st.markdown("<span style='color:#fbbf24; font-family:monospace; font-size:13px; font-weight:500;'>-- POWER HOUR 16:00-18:00 GST</span>", unsafe_allow_html=True)
    st.markdown("<p style='color:#10b981; font-family:monospace; font-size:12px; margin-top:2px;'>BOS CONFIRMED • FVG VACUUM UNMITIGATED</p>", unsafe_allow_html=True)

    # Reconstruct Candle Vector Graphs
    np.random.seed(42)
    t_bars = pd.date_range(end=datetime.now(), periods=45, freq='15min')
    prices = np.sin(np.linspace(0, 4.5, 45)) * 18 + 3402
    opens = prices[:-1] + np.random.normal(0, 1.2, 44)
    closes = prices[1:] + np.random.normal(0, 1.2, 44)
    highs = np.maximum(opens, closes) + np.random.uniform(0.5, 3.5, 44)
    lows = np.minimum(opens, closes) - np.random.uniform(0.5, 3.5, 44)

    # Injecting anomalous massive Institutional Expansion Candle at Index 25
    opens[25], highs[25], lows[25], closes[25] = 3393.10, 3422.40, 3392.00, 3421.10

    fig = go.Figure(data=[go.Candlestick(
        x=t_bars[:-1], open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#10b981', decreasing_line_color='#ef5350',
        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef5350'
    )])

    # --- Overlaying High-End Structural Shapes Matrices ---
    # FVG Vacuum Imbalance Box (Light Blue)
    fig.add_shape(type="rect", x0=t_bars[25], y0=3412.00, x1=t_bars[-1], y1=3421.10, fillcolor="rgba(96, 165, 250, 0.08)", line=dict(width=0))
    # Bullish Demand Order Block Box (Dark Blue)
    fig.add_shape(type="rect", x0=t_bars[22], y0=3392.00, x1=t_bars[26], y1=3402.00, fillcolor="rgba(59, 130, 246, 0.15)", line=dict(width=1, color="rgba(59,130,246,0.4)"))

    # Target Structural Price Benchmark Lines
    fig.add_trace(go.Scatter(x=[t_bars[25], t_bars[-1]], y=[3412.00, 3412.00], mode="lines", line=dict(color="#60a5fa", width=1.5, dash="dash"), name="FVG Open"))
    fig.add_trace(go.Scatter(x=[t_bars[22], t_bars[-1]], y=[3402.00, 3402.00], mode="lines", line=dict(color="#10b981", width=1.5), name="Entry Limit"))
    fig.add_trace(go.Scatter(x=[t_bars[22], t_bars[-1]], y=[3392.00, 3392.00], mode="lines", line=dict(color="#ef5350", width=1.5, dash="dot"), name="Invalidation SL"))

    fig.update_layout(
        template="plotly_dark", xaxis_rangeslider_visible=False, height=360,
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#21262d', side="right")
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Operational Dual Control Buttons
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

    # Metadata System Engine Metrics Section Layout
    st.write(" ")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("""
            <table style='width:100%; border:none; border-collapse:collapse;'>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>ENGINE</td><td class='meta-value' style='color:#10b981;'>AUTONOMOUS ACTIVE</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>MODELS</td><td class='meta-value'>A:OrderBlock Demand B:FVG-Retest</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>CLOCK</td><td class='meta-value'>16:10 GST • Standing By</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>TRADES</td><td class='meta-value'>2 open positions • 2/3 allocated</td></tr>
            </table>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
            <table style='width:100%; border:none; border-collapse:collapse;'>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>RISK MATRIX</td><td class='meta-value' style='color:#f87171;'>1% Maximum = ${live_balance * 0.01:.2f}</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>ENTRY RULES</td><td class='meta-value'>Limit orders strictly • No chasing</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>ACCOUNT SYNC</td><td class='meta-value'>Exness Terminal Stream connected</td></tr>
                <tr style='border-bottom: 1px solid #21262d; height:32px;'><td class='meta-label'>LIVE SEED</td><td class='meta-value' style='color:#60a5fa;'>Balance: ${live_balance:.2f}</td></tr>
            </table>
        """, unsafe_allow_html=True)

    # --- 🟢 UPGRADE: MARKED ON THIS CHART COMPREHENSIVE ANALYSIS PANEL ---
    st.write(" ")
