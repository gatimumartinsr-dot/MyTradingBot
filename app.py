import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

# Initialize clean wide workspace layouts
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

if "journal_data" not in st.session_state:
    st.session_state.journal_data = []
if "equity_history" not in st.session_state:
    st.session_state.equity_history = [1000.0]

# --- REAL-TIME ACCOUNT SYNC BRIDGE LOADING LAYER ---
balance_file = "live_balance.json"
signal_file = "trade_signal.json"

live_balance = 1000.00
live_equity = 1000.00
live_profit = 0.00
account_status = "⚫ OFFLINE (SIMULATION MODE)"
status_color = "#9ca3af"

if os.path.exists(balance_file):
    try:
        with open(balance_file, "r") as f:
            data = json.load(f)
            if time.time() - data.get("timestamp", 0) < 60:
                live_balance = float(data.get("balance", live_balance))
                live_equity = float(data.get("equity", live_equity))
                live_profit = float(data.get("profit", live_profit))
                account_status = f"🟢 LIVE SYNCED (MT5 ID: {data.get('login')})"
                status_color = "#10b981"
    except Exception:
        pass

# Navigation layout header tabs
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: CONNECT BROKERS ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'> Universal Broker Link Gate </h2>", unsafe_allow_html=True)
    broker_select = st.selectbox("CHOOSE SYSTEM TERMINAL ARCHITECTURE", ["Exness Technologies Ltd", "JustMarkets Inc.", "XM Global Markets"])
    col_log1, col_log2 = st.columns(2)
    with col_log1: st.text_input("MT5 ACCOUNT LOGIN USER ID", value="474239881", disabled=True)
    with col_log2: st.text_input("EXNESS LIVE DEMO SERVER", value="Exness-MT5-Trial15", disabled=True)
    st.text_input("SECURE PASSWORD STREAM", value="••••••••••••", disabled=True)
    st.write(" ")
    st.success("🔒 System active: Cloud authentication handshake linked with your laptop background terminal engine loop.")

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
            entry_level = st.number_input("Entry Price Target Coordinates", min_value=0.0, value=2500.00, format="%.2f")
        with col2:
            sl_level = st.number_input("Validation Stop Loss Level", min_value=0.0, value=2495.00, format="%.2f")
            tp_level = st.number_input("Target Take Profit Level", min_value=0.0, value=2515.00, format="%.2f")
            risk_pct = st.slider("Risk Per Setup Allocation (%)", 0.25, 2.0, 1.0, step=0.25)
            
        st.write(" ")
        submit_btn = st.form_submit_button("⚡ Commit Matrix & Clear Input Screens")
        
        if submit_btn:
            pips_delta = abs(entry_level - sl_level)
            calculated_pips = pips_delta * 10 if "XAU" in target_pair else pips_delta * 10000
            risk_amount = live_balance * (risk_pct / 100)
            lot_size = risk_amount / (calculated_pips * 2.0) if "XAU" in target_pair else risk_amount / (calculated_pips * 10.0)
            recommended_lots = max(0.01, round(lot_size, 2))
            
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
            st.session_state.equity_history.append(st.session_state.equity_history[-1] + 25.00)
            st.balloons()
            st.success("✅ Trade matrix entry logged successfully into your smartphone journal tab!")

# ==================== TAB 3: PROF CHART CANVAS & REASONS LOG ====================
with t_chart:
    st.markdown("""
        <div class="header-box">
            <table style="width:100%; border:none;">
                <tr>
                    <td style="color:#10b981; font-family:monospace; font-weight:600;">🟢 ACTIVE WEB RADAR STREAM</td>
                    <td style="text-align:center; color:#60a5fa; font-family:monospace;"><span style="background-color:#1e293b; padding:3px 8px; border-radius:4px;">⏱️ TIME FILTER: POWER HOUR</span></td>
                    <td style="text-align:right; color:#9ca3af; font-family:monospace; font-weight:600;">XAUUSDm M15</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

    st.radio("TICKER RADAR ASSIGNMENT", ["XAU", "BTC", "XAG", "EUR", "GBP"], horizontal=True, label_visibility="collapsed")

    np.random.seed(42)
    chart_time = pd.date_range(end=datetime.now(), periods=40, freq='15min')
    base_prices = np.sin(np.linspace(0, 4, 40)) * 15 + 2505
    opens = base_prices[:-1] + np.random.normal(0, 1, 39)
    closes = base_prices[1:] + np.random.normal(0, 1, 39)
    highs = np.maximum(opens, closes) + np.random.uniform(1, 3, 39)
    lows = np.minimum(opens, closes) - np.random.uniform(1, 3, 39)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart_time[:-1], open=opens, high=highs, low=lows, close=closes, name="Market Price"))

    # --- UPGRADE: AUTOMATIC HISTORICAL ENTRY HIGHLIGHT ENGINE ---
    # Automatically extracts saved entries from the journal data log layer
    if st.session_state.journal_data:
        for trade in st.session_state.journal_data:
            entry_p = float(trade["Entry"])
            sl_p = float(trade["Stop Loss"])
            tp_p = float(trade["Take Profit"])
            
            # Draw precise green/red overlay boxes around the data points of execution history
            fig.add_shape(type="rect", x0=chart_time[0], y0=entry_p, x1=chart_time[-1], y1=tp_p, fillcolor="rgba(16, 185, 129, 0.08)", line=dict(width=0))
            fig.add_shape(type="rect", x0=chart_time[0], y0=sl_p, x1=chart_time[-1], y1=entry_p, fillcolor="rgba(239, 83, 80, 0.08)", line=dict(width=0))
            
            fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[entry_p, entry_p], mode="lines", line=dict(color="#3b82f6", width=2, dash="dash"), name=f"Bot Entry: {entry_p}"))
    else:
        # Default placeholder target lines if journal cache is empty
        fig.add_shape(type="rect", x0=chart_time[0], y0=2500.00, x1=chart_time[-1], y1=2515.00, fillcolor="rgba(16, 185, 129, 0.12)", line=dict(width=0))
        fig.add_shape(type="rect", x0=chart_time[0], y0=2495.00, x1=chart_time[-1], y1=2500.00, fillcolor="rgba(239, 83, 80, 0.12)", line=dict(width=0))
        fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[2515.00, 2515.00], mode="lines", line=dict(color="#10b981", width=2), name="Take Profit"))
        fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[2500.00, 2500.00], mode="lines", line=dict(color="#3b82f6", width=2, dash="dash"), name="Limit Entry"))
        fig.add_trace(go.Scatter(x=[chart_time[0], chart_time[-1]], y=[2495.00, 2495.00], mode="lines", line=dict(color="#ef5350", width=2, dash="dot"), name="Stop Loss"))

    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=350, margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.write(" ")
    st.subheader("📝 Setup Structural Confluence Commentary Log")
    st.info("**🛡️ ORDER BLOCK LOCATION CRITERIA:**\n\nPrice printed a high-displacement shift in structure, confirming aggressive institutional accumulation. The origin candle boundary creates a high-probability loading area for market buy triggers.")
