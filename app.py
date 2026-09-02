import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

# Custom premium styling block to mimic the exact colors, metrics, and pill buttons from your mockup
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
        }
        .btn-flatten>button {
            background-color: #3b2326 !important;
            color: #f87171 !important;
            border: 1px solid #7f1d1d !important;
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
    </style>
""", unsafe_allow_html=True)

# Initialize memory configurations
if "journal_data" not in st.session_state:
    st.session_state.journal_data = []

# Top Navigation Tabs Bar
tabs = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# Skip formatting Sign In / Dashboard to keep this update laser-focused on your professional Chart tab layout
with tabs[0]: st.info("Connection module operational.")
with tabs[1]: st.info("Dashboard workspace ready.")

# ==================== TAB 3: PROFESSIONAL CHART ENGINE ====================
with tabs[2]:
    # Header Session Status Matrix Row
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        st.markdown("<span style='font-family: monospace; color: #10b981;'>🟢 14:09 GST</span> &nbsp;&nbsp; <span style='font-family: monospace; color: #9ca3af; background-color: #1e293b; padding: 2px 6px; border-radius: 4px;'>⚫ OFFLINE</span>", unsafe_allow_html=True)
    with col_h2:
        st.markdown("<p style='text-align: right; font-family: monospace; color: #60a5fa;'>DEMO • EXNESS</p>", unsafe_allow_html=True)
        
    # Ticker Price Metrics and Asset Picker row
    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        st.markdown("<h2 style='margin:0; padding:0; color:white;'>XAUUSD <span style='font-size:12px; color:#4b5563;'>EXNESS M15</span></h2>", unsafe_allow_html=True)
        st.markdown("<h1 style='margin:0; padding:0; color:white; font-family: monospace;'>3,408.60 <span style='font-size:16px; color:#10b981;'>+0.38%</span></h1>", unsafe_allow_html=True)
    with col_t2:
        # Asset selector pill simulation menu
        st.write(" ")
        st.radio("WATCHLIST TICKER ASSET", ["XAU", "BTC", "XAG", "EUR", "GBP"], horizontal=True, label_visibility="collapsed")

    # Strategy Guidelines Overlay Banner Text
    st.markdown("<p style='color:#fbbf24; font-family:monospace; margin-bottom:2px;'>-- POWER HOUR 16:00-18:00 GST</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#10b981; font-family:monospace; margin-top:0;'>BOS CONFIRMED • FVG OPEN</p>", unsafe_allow_html=True)

    # Professional Chart Canvas Section
    # Generates precise mock trading candlestick bars tracking market structure vectors
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

    # Draw precise horizontal lines mirroring institutional zones from your guide
    fig.add_hline(y=3412.00, line_dash="dash", line_color="#3b82f6", annotation_text="ENTRY 3,412.00", annotation_position="top right")
    fig.add_hline(y=3405.00, line_dash="dash", line_color="#fbbf24", annotation_text="OB ZONE 3,405.00", annotation_position="top right")
    fig.add_hline(y=3392.00, line_dash="dash", line_color="#ef5350", annotation_text="SL 3,392.00", annotation_position="top right")

    fig.update_layout(
        template="plotly_dark", xaxis_rangeslider_visible=False, height=380,
        margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1f2d3d')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # High-Priority Dual Operational Control Buttons
    st.write(" ")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.markdown('<div class="btn-review">', unsafe_allow_html=True)
        st.button("Review setup", key="review_btn")
        st.markdown('</div>', unsafe_allow_html=True)
    with btn_col2:
        st.markdown('<div class="btn-flatten">', unsafe_allow_html=True)
        st.button("Flatten all", key="flatten_btn")
        st.markdown('</div>', unsafe_allow_html=True)

    # Engine Metrics Grid Data Section
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

# Remaining tabs logic blocks configurations
with tabs[3]: st.info("Setup gating checklists operational.")
with tabs[4]: st.info("Historical journal logs dashboard active.")
with tabs[5]: st.info("System guidelines library active.")
with tabs[6]: st.info("API communication webhooks configured.")
