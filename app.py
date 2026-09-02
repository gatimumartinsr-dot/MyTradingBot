import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Initialize the force layout styling options first
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
    </style>
""", unsafe_allow_html=True)

# Persistent storage arrays mapping parameters cleanly
if "journal_data" not in st.session_state:
    st.session_state.journal_data = []
if "equity_history" not in st.session_state:
    st.session_state.equity_history = [500.0, 505.0, 498.0, 512.0, 525.0]

# --- CORRECTED LINKED NAVIGATION TABS MODULE STRUCTURING ---
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: SIGN IN ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'>🟢 HELIX OB</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #9ca3af; font-weight: 300; margin-bottom: 25px;'>Three things, and you're trading.</h3>", unsafe_allow_html=True)
    
    broker_select = st.radio("1 - YOUR BROKER", ["Exness", "IC Markets", "Pepperstone", "Other MT5"], horizontal=True)
    st.write(" ")
    acc_num = st.text_input("2 - ACCOUNT NUMBER", value="474 239 881", placeholder="474 239 881")
    acc_pass = st.text_input("3 - PASSWORD", type="password", value="password123", placeholder="••••••••••••")
    st.write(" ")
    acc_type = st.radio("ACCOUNT TYPE", ["Demo account", "Live account"], horizontal=True)
    st.write(" ")
    if st.button("Connect my account", type="primary", use_container_width=True):
        st.success("🔗 Exness account linkage pipeline connected cleanly!")

# ==================== TAB 2: DASHBOARD ====================
with t_dashboard:
    st.subheader("📊 Live Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value="$500.00")
    with m_col2: st.metric(label="Floating Equity", value="$500.00")
    with m_col3: st.metric(label="Active Open Profit/Loss", value="$0.00")
        
    st.divider()
    st.subheader("🤖 Mobile Order Dispatch Console")
    col1, col2 = st.columns(2)
    with col1:
        direction = st.selectbox("Blueprint", ["BUY_LIMIT", "SELL_LIMIT"])
        target_pair = st.selectbox("Watchlist Asset", ["XAUUSDm", "EURUSD", "GBPUSD"])
        entry_level = st.number_input("Entry Target Price", value=3412.00, format="%.2f")
    with col2:
        sl_level = st.number_input("Stop Loss Level", value=3392.00, format="%.2f")
        tp_level = st.number_input("Take Profit Level", value=3450.00, format="%.2f")
        risk_pct = st.slider("Risk Per Setup (%)", 0.25, 2.0, 1.0, step=0.25)
        
    st.write(" ")
    if st.button("⚡ Dispatch Trade Blueprint straight to Matrix", use_container_width=True):
        new_record = {"Time (GST)": datetime.now().strftime('%Y-%m-%d %H:%M'), "Asset": target_pair, "Action": direction, "Entry": entry_level, "Stop Loss": sl_level, "Take Profit": tp_level, "Allocated Volume": 0.45}
        st.session_state.journal_data.append(new_record)
        st.session_state.equity_history.append(st.session_state.equity_history[-1] + 15.00)
        st.balloons()
        st.success("✅ Trade matrix entry logged successfully.")

# ==================== TAB 3: CHART ====================
with t_chart:
    # Meta Status Header Row Block Element layout
    st.markdown("""
        <div class="header-box">
            <table style="width:100%; border:none;">
                <tr>
                    <td style="color:#10b981; font-family:monospace; font-weight:600;">🟢 14:09 GST</td>
                    <td style="text-align:center; color:#9ca3af; font-family:monospace;"><span style="background-color:#1e293b; padding:3px 8px; border-radius:4px;">⚫ OFFLINE</span></td>
                    <td style="text-align:right; color:#60a5fa; font-family:monospace; font-weight:600;">DEMO • EXNESS</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)
        
    # Asset parameters tracker indicators line rows
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        st.markdown("<h2 style='margin:0; padding:0; color:white;'>XAUUSD <span style='font-size:12px; color:#4b5563;'>EXNESS M15</span></h2>", unsafe_allow_html=True)
        st.markdown("<h1 style='margin:0; padding:0; color:white; font-family: monospace;'>3,408.60 <span style='font-size:16px; color:#10b981;'>+0.38%</span></h1>", unsafe_allow_html=True)
    with col_t2:
        st.radio("TICKER", ["XAU", "BTC", "XAG", "EUR", "GBP"], horizontal=True, label_visibility="collapsed")

    st.markdown("<p style='color:#fbbf24; font-family:monospace; margin-bottom:2px; font-weight:500;'>-- POWER HOUR 16:00-18:00 GST</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#10b981; font-family:monospace; margin-top:0; font-weight:500;'>BOS CONFIRMED • FVG OPEN</p>", unsafe_allow_html=True)

    # Generating Candle Vector Matrices charts components
    np.random.seed(42)
    chart_time = pd.date_range(end=datetime.now(), periods=40, freq='15min')
    base_prices = np.sin(np.linspace(0, 5, 40)) * 20 + 3400
    opens = base_prices[:-1] + np.random.normal(0, 2, 39)
    closes = base_prices[1:] + np.random.normal(0, 2, 39)
    highs = np.maximum(opens, closes) + np.random.uniform(1, 5, 39)
    lows = np.minimum(opens, closes) - np.random.uniform(1, 5, 39)

    fig = go.Figure(data=[go.Candlestick(
        x=chart_time[:-1], open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#10b981', decreasing_line_color='#ef5350',
        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef5350'
    )])

    fig.add_hline(y=3412.00, line_dash="dash", line_color="#3b82f6", annotation_text="ENTRY 3,412.00", annotation_position="top right")
    fig.add_hline(y=3405.00, line_dash="dash", line_color="#fbbf24", annotation_text="OB ZONE 3,405.00", annotation_position="top right")
    fig.add_hline(y=3392.00, line_dash="dash", line_color="#ef5350", annotation_text="SL 3,392.00", annotation_position="top right")

    fig.update_layout(
        template="plotly_dark", xaxis_rangeslider_visible=False, height=360,
        margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1f2d3d')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Operational Action Control Interfaces Buttons Section Rows
    st.write(" ")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.markdown('<div class="btn-review">', unsafe_allow_html=True)
        st.button("Review setup", key="review_btn_c")
        st.markdown('</div>', unsafe_allow_html=True)
    with btn_col2:
        st.markdown('<div class="btn-flatten">', unsafe_allow_html=True)
        st.button("Flatten all", key="flatten_btn_c")
        st.markdown('</div>', unsafe_allow_html=True)

    # Logging layout dashboard grid text elements sections
    st.write(" ")
    st.markdown("""
        <table class="metric-table">
            <tr><td>ENGINE</td><td class="metric-value" style="color:#10b981 !important;">DEMO DATA</td></tr>
            <tr><td>MODELS</td><td class="metric-value">A:OrderBlock B:S&R-retest</td></tr>
            <tr><td>CLOCK</td><td class="metric-value">14:09 GST • standing by</td></tr>
            <tr><td>TRADES</td><td class="metric-value">2 open • 2/3 used today</td></tr>
            <tr><td>RISK</td><td class="metric-value" style="color:#fbbf24 !important;">1% = $509.32 per trade</td></tr>
            <tr><td>ENTRIES</td><td class="metric-value">limit only • never chases</td></tr>
            <tr><td>SOURCE</td><td class="metric-value">sample data – connect MT5 for live</td></tr>
        </table>
    """, unsafe_allow_html=True)

# ==================== TAB 4: SETUP GATE ====================
with t_gate:
    st.subheader("🛡️ Institutional Setup Validation Checklist")
    st.write("Verify the system guidelines metrics to clear the locks channels:")
    
    r1 = st.checkbox("🔍 Price structural mitigation has tapped into unmitigated Order Block (OB)")
    r2 = st.checkbox("⚡ High-volume momentum expansion left a valid 3-candle Fair Value Gap (FVG)")
    r3 = st.checkbox("📈 Current pricing baseline structure is fully aligned with 200 MA trend vector")
