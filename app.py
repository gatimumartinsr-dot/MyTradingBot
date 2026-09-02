import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Institutional Confluence Engine", layout="wide", page_icon="🦅")
st.title("🦅 Exness Mobile Automation Hub")

# Initial Session State initialization for trade journaling log storage
if "journal_data" not in st.session_state:
    st.session_state.journal_data = []

# Left Sidebar Controls
st.sidebar.header("🎯 Operational Risk Parameters")
account_balance = st.sidebar.number_input("Account Balance ($)", value=500)
risk_pct = st.sidebar.slider("Risk Limit Per Setup (%)", 0.25, 2.0, 1.0, step=0.25)
target_pair = st.sidebar.selectbox("Select Watchlist Asset", ["XAUUSDm", "EURUSD", "GBPUSD"])

st.divider()

# --- 1. SIMULATED CHART FEEDS WINDOWS ---
st.subheader("📈 Live Structural Market Review")
# Creates fake structural coordinates for mobile sandbox simulation charting
chart_time = pd.date_range(end=datetime.now(), periods=30, freq='15min')
fig = go.Figure(data=[go.Candlestick(
    x=chart_time,
    open=np.random.uniform(2400, 2420, 30), high=np.random.uniform(2420, 2430, 30),
    low=np.random.uniform(2380, 2400, 30), close=np.random.uniform(2400, 2420, 30),
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
)])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=350, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 2. MOBILE DISPATCH ORDER BLUEPRINT PANEL ---
st.subheader("🤖 Mobile Order Dispatch Console")
col1, col2, col3, col4 = st.columns(4)
with col1:
    direction = st.selectbox("Order Blueprint", ["BUY_LIMIT", "SELL_LIMIT"])
with col2:
    entry_level = st.number_input("Order Entry Target Price", value=0.0, format="%.2f")
with col3:
    sl_level = st.number_input("Stop Loss Target Level (Wick Edge)", value=0.0, format="%.2f")
with col4:
    tp_level = st.number_input("Take Profit Target Level", value=0.0, format="%.2f")

# Processing pipeline for positioning risk parameters
if entry_level > 0 and sl_level > 0:
    pips_delta = abs(entry_level - sl_level)
    calculated_pips = pips_delta * 10 if "XAU" in target_pair else pips_delta * 10000
    risk_amount = account_balance * (risk_pct / 100)
    
    # Lot Calculation Logic Model
    if "XAU" in target_pair:
        lot_size = risk_amount / (calculated_pips * 2.0)
    else:
        lot_size = risk_amount / (calculated_pips * 10.0)
    recommended_lots = max(0.01, round(lot_size, 2))
    
    st.success(f"📊 Matrix Output: Risking **${round(risk_amount, 2)}** | Stop Distance: **{round(calculated_pips, 1)} Pips** | Dynamic Lot Allocation: **{recommended_lots} Lots**")

if st.button("⚡ Dispatch Trade Blueprint straight to Mobile Journal", type="primary"):
    if entry_level > 0:
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
        st.balloons()
        st.success("✅ Blueprint logged! Use your MT5 application parameters to complete execution steps.")

# --- 3. RUNNING JOURNAL DATA LOG LEDGER GRID ---
st.divider()
st.subheader("🗒️ Smartphone Active Order Journal")
if st.session_state.journal_data:
    df_j = pd.DataFrame(st.session_state.journal_data)
    st.dataframe(df_j.sort_index(ascending=False), use_container_width=True)
else:
    st.info("ℹ️ Account Ledger Sandbox Clear: Use the console above to submit entries live via your device screens.")
