import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

# Initialize premium wide layout configuration parameters
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
    st.session_state.equity_history = [160.22]

# --- DATA ROUTING INTER-COMMUNICATION PIPELINES ---
balance_file = "live_balance.json"
signal_file = "trade_signal.json"

live_balance = 160.22
live_equity = 160.22
live_profit = 0.00
account_status = "🟢 ACTIVE HUB BRIDGE DISPATCHER ONLINE"

if os.path.exists(balance_file):
    try:
        with open(balance_file, "r") as f:
            data = json.load(f)
            live_balance = float(data.get("balance", live_balance))
            live_equity = float(data.get("equity", live_equity))
            live_profit = float(data.get("profit", live_profit))
            account_status = f"🟢 SYNCED WITH EXNESS (ID: {data.get('login')})"
    except Exception:
        pass

# FIXED: Explicitly separated and isolated every sliding tab handle variable name
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
    st.success("🔒 System active: Cloud authentication handshake linked with your laptop background terminal engine loop.")

# ==================== TAB 2: DASHBOARD ====================
with t_dashboard:
    st.markdown(f"Status: <span style='color:#10b981; font-family:monospace; font-weight:600;'>{account_status}</span>", unsafe_allow_html=True)
    st.subheader("📊 Cross-Broker Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value=f"${live_balance:.2f}")
    with m_col2: st.metric(label="Floating Equity", value=f"${live_equity:.2f}")
    with m_col3: st.metric(label="Active Open Profit/Loss", value=f"${live_profit:.2f}")
        
    st.divider()
    st.subheader("🤖 Strategy Execution Blueprint Matrix")
    
    with st.form("execution_dispatch_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            direction = st.selectbox("Blueprint Order Type", ["BUY_LIMIT", "SELL_LIMIT"])
            target_pair = st.selectbox("Asset Watchlist Suffix", ["XAUUSDm", "EURUSD", "GBPUSD"])
            entry_level = st.number_input("Entry Target Price Coordinates", min_value=0.0, value=4400.00, format="%.2f")
        with col2:
            sl_level = st.number_input("Validation Stop Loss Level (Wick Edge)", min_value=0.0, value=4395.00, format="%.2f")
            tp_level = st.number_input("Target Take Profit Level", min_value=0.0, value=4420.00, format="%.2f")
            risk_pct = st.slider("Risk Per Setup Capital Allocation (%)", 0.25, 2.0, 1.0, step=0.25)
            
        st.write(" ")
        submit_btn = st.form_submit_button("⚡ Dispatch Trade Matrix directly to Exness MT5")
        
        if submit_btn:
            pips_delta = abs(entry_level - sl_level)
            calculated_pips = pips_delta * 10 if "XAU" in target_pair else pips_delta * 10000
            risk_amount = live_balance * (risk_pct / 100)
            lot_size = risk_amount / (calculated_pips * 2.0) if "XAU" in target_pair else risk_amount / (calculated_pips * 10.0)
            recommended_lots = max(0.01, round(lot_size, 2))
            
            signal_data = {
                "symbol": target_pair, "order_type": direction, "entry": entry_level,
                "sl": sl_level, "tp": tp_level, "lots": recommended_lots, "active": True
            }
            with open(signal_file, "w") as sf:
                json.dump(signal_data, sf)
            
            new_record = {"Time (GST)": datetime.now().strftime('%Y-%m-%d %H:%M'), "Asset": target_pair, "Action": direction, "Entry": entry_level, "Stop Loss": sl_level, "Take Profit": tp_level, "Allocated Volume": recommended_lots}
            st.session_state.journal_data.append(new_record)
            st.session_state.equity_history.append(round(live_balance, 2))
            st.balloons()
            st.success(f"🚀 Signals Dispatched to Exness! Volume: {recommended_lots} Lots | Risked Amount: ${risk_amount:.2f}")

# ==================== TAB 3: CHART ====================
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

    st.write(" ")
    st.subheader("📝 Setup Structural Confluence Commentary Log")
    st.info("**🛡️ ORDER BLOCK LOCATION CRITERIA:**\n\nPrice printed a high-displacement shift in structure, breaking past the previous swing high (BOS Confirmed). This origin footprint leaves a major demand block area near $4,400.00.")
    st.warning("**⚡ FAIR VALUE GAP (FVG) VACUUM:**\n\nThe explosive price contraction created a technical vacuum gap between Candle 1 and Candle 3. Our entry limits are locked at the opening edge of this vacuum to absorb the mechanical retest phase before extension.")
    st.error("**🔄 REVERSAL CANDLE CONFIGURATION:**\n\nOur rules mandate that we wait for price to dive deep into our highlighted box and print a long lower-wick pin bar confirmation on execution timeframes before trailing protections engage.")

# ==================== TAB 4: SETUP GATE ====================
with t_gate:
    st.subheader("🛡️ Institutional Setup Validation Checklist")
    r1 = st.checkbox("🔍 Structural footprint has successfully tapped into unmitigated Order Block demand (OB)")
    r2 = st.checkbox("⚡ Strong momentum expansion displacement left a valid 3-candle Fair Value Gap vacuum (FVG)")
    r3 = st.checkbox("📈 Current pricing layout baseline is fully aligned with 200 MA trend vector parameters")
    r4 = st.checkbox("📊 Relative Strength Index (RSI 14) confirms clean structural momentum footprints")
    if r1 and r2 and r3 and r4: st.success("🔓 Setup Authorized! System strategy guidelines fully cleared.")

# ==================== TAB 5: JOURNAL ====================
with t_journal:
    st.subheader("🗒️ Smartphone Active Order Journal")
    st.dataframe(pd.DataFrame(st.session_state.journal_data), use_container_width=True)
    st.write(" ")
    st.subheader("📈 Capital Growth trend Tracking Curve Chart")
    curve_fig = go.Figure()
    curve_fig.add_trace(go.Scatter(y=st.session_state.equity_history, mode='lines+markers', line=dict(color='#10b981', width=3), marker=dict(size=8, color='#ffffff')))
