import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Initialize clean wide layouts
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

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
        }
        .btn-review>button {
            background-color: #10b981 !important;
            color: #060b0d !important;
            border: none !important;
            width: 100% !important;
        }
        .btn-flatten>button {
            background-color: #3b2326 !important;
            color: #f87171 !important;
            border: 1px solid #7f1d1d !important;
            width: 100% !important;
        }
        .metric-table {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            color: #9ca3af !important;
            width: 100%;
        }
        .metric-value {
            color: #e5e7eb !important;
            text-align: right;
        }
        .header-box {
            background-color: #111827;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #1f2937;
            margin-bottom: 15px;
        }
        .journal-box {
            background-color: #161e29;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #223147;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

if "journal_data" not in st.session_state:
    st.session_state.journal_data = []
if "equity_history" not in st.session_state:
    st.session_state.equity_history = [500.0, 505.0, 498.0, 512.0, 525.0]

# --- SLIDING NAV SYSTEMS BAR ---
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: SIGN IN ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'>🟢 HELIX OB SECURITY PORTAL</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #9ca3af; font-weight: 300; margin-bottom: 25px;'>Authentication protocols actively hidden.</h3>", unsafe_allow_html=True)
    
    broker_select = st.radio("SELECT BROKER ARCHITECTURE", ["Exness", "IC Markets", "Pepperstone"], horizontal=True)
    st.write(" ")
    acc_num = st.text_input("ACCOUNT ID METRIC", value="474239881", type="password", placeholder="Enter Account Identification Number")
    acc_pass = st.text_input("TRADING EXECUTION TERMINAL PASSWORD", value="ExnessSecret2026", type="password", placeholder="••••••••••••")
    st.write(" ")
    acc_type = st.radio("SERVER SELECTION ENVIRONMENT", ["Demo Environment sandbox", "Live Market Pipelines"], horizontal=True)
    st.write(" ")
    if st.button("Connect Secure Cloud Handoff", type="primary", use_container_width=True):
        st.success("🔒 Secure verification accepted. Connection elements successfully hidden from display screens!")

# ==================== TAB 2: DASHBOARD ====================
with t_dashboard:
    st.subheader("📊 Live Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value=f"${st.session_state.equity_history[-1]:.2f}")
    with m_col2: st.metric(label="Floating Equity", value=f"${st.session_state.equity_history[-1]:.2f}")
    with m_col3: st.metric(label="Active Open Profit/Loss", value="$0.00")
        
    st.divider()
    st.subheader("🤖 Mobile Order Dispatch Console")
    
    with st.form("clearable_dispatch_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            direction = st.selectbox("Blueprint Framework", ["BUY_LIMIT", "SELL_LIMIT"])
            target_pair = st.selectbox("Watchlist Target Asset", ["XAUUSDm", "EURUSD", "GBPUSD"])
            entry_level = st.number_input("Entry Price Target Coordinates", min_value=0.0, value=3412.00, format="%.2f")
        with col2:
            sl_level = st.number_input("Validation Stop Loss Level", min_value=0.0, value=3392.00, format="%.2f")
            tp_level = st.number_input("Target Take Profit Level", min_value=0.0, value=3460.00, format="%.2f")
            risk_pct = st.slider("Risk Limit Per Setup Allocation (%)", 0.25, 2.0, 1.0, step=0.25)
            
        st.write(" ")
        submit_btn = st.form_submit_button("⚡ Commit Matrix & Flush Entry Screen", use_container_width=True)
        
        if submit_btn:
            pips_delta = abs(entry_level - sl_level)
            calculated_pips = pips_delta * 10 if "XAU" in target_pair else pips_delta * 10000
            risk_amount = st.session_state.equity_history[-1] * (risk_pct / 100)
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
            st.session_state.equity_history.append(st.session_state.equity_history[-1] + 18.50)
            st.balloons()
            st.success("✅ Trade matrix entry logged successfully. Inputs completely cleared for your next setup configuration!")

# ==================== TAB 3: CHART ====================
with t_chart:
    st.markdown("""
        <div class="header-box">
            <table style="width:100%; border:none;">
                <tr>
                    <td style="color:#10b981; font-family:monospace; font-weight:600;">🟢 ACTIVE RADAR STREAM</td>
                    <td style="text-align:center; color:#60a5fa; font-family:monospace;"><span style="background-color:#1e293b; padding:3px 8px; border-radius:4px;">⏱️ DUBAI SESSION: POWER HOUR</span></td>
                    <td style="text-align:right; color:#9ca3af; font-family:monospace; font-weight:600;">XAUUSDm M15</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

    st.radio("TICKER RADAR ASSIGNMENT", ["XAU", "BTC", "XAG", "EUR", "GBP"], horizontal=True, label_visibility="collapsed")

    np.random.seed(88)
    chart_time = pd.date_range(end=datetime.now(), periods=40, freq='15min')
    base_prices = np.sin(np.linspace(0, 4, 40)) * 25 + 3410
    opens = base_prices[:-1] + np.random.normal(0, 2, 39)
    closes = base_prices[1:] + np.random.normal(0, 2, 39)
    highs = np.maximum(opens, closes) + np.random.uniform(1, 4, 39)
    lows = np.minimum(opens, closes) - np.random.uniform(1, 4, 39)

    fig = go.Figure(data=[go.Candlestick(
        x=chart_time[:-1], open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#10b981', decreasing_line_color='#ef5350',
        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef5350'
    )])

    fig.add_shape(type="rect", x0=chart_time[0], y0=3412.00, x1=chart_time[-1], y1=3460.00, fillcolor="rgba(16, 185, 129, 0.15)", line=dict(width=0))
    fig.add_shape(type="rect", x0=chart_time[0], y0=3392.00, x1=chart_time[-1], y1=3412.00, fillcolor="rgba(239, 83, 80, 0.15)", line=dict(width=0))

    fig.add_hline(y=3460.00, line_dash="solid", line_color="#10b981", annotation_text="TP TARGET: 3,460.00", annotation_position="top right")
    fig.add_hline(y=3412.00, line_dash="dash", line_color="#3b82f6", annotation_text="LIMIT ENTRY: 3,412.00", annotation_position="top right")
    fig.add_hline(y=3405.00, line_dash="solid", line_color="#fbbf24", annotation_text="INSTITUTIONAL ORDER BLOCK ZONE", annotation_position="bottom right")
    fig.add_hline(y=3392.00, line_dash="dash", line_color="#ef5350", annotation_text="RISK SL: 3,392.00", annotation_position="bottom right")

    fig.update_layout(
        template="plotly_dark", xaxis_rangeslider_visible=False, height=390,
        margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1f2d3d')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.write(" ")
    st.subheader("📝 Setup Structural Confluence Commentary Log")
    
    st.markdown("""
        <div class="journal-box">
            <h5 style='color:#60a5fa; margin-bottom:5px; font-family:monospace;'>🛡️ WHY WAS THIS ORDER BLOCK TAKEN?</h5>
            <p style='color:#d1d5db; font-size:14px; margin-top:0;'>Price generated a significant high-volume displacement upwards, violently breaking past the previous minor swing structure (BOS Confirmed). This left a highly defined, unmitigated institutional footprint candle block at the origin point ($3,405.00) which serves as our major structural demand loading area.</p>
            <h5 style='color:#fbbf24; margin-bottom:5px; font-family:monospace;'>⚡ WHY WAS THIS SPECIFIC FVG DRIVEN AS AN ENTRY ZONE?</h5>
