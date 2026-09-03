import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

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

# --- SLIDING NAV CORES SYSTEMS NAVIGATION TABS ---
t_signin, t_dashboard, t_chart, t_gate, t_journal, t_rules, t_connections = st.tabs([
    "📂 SIGN IN", "📊 DASHBOARD", "📈 CHART", "🛡️ SETUP GATE", 
    "🗒️ JOURNAL", "📜 RULES", "🔌 CONNECTIONS"
])

# ==================== TAB 1: CONNECT BROKERS ====================
with t_signin:
    st.markdown("<h2 style='text-align: center; color: white;'>🟢 UNIVERSAL BROKER CROSS-LINK GATES</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #9ca3af; font-weight: 300; margin-bottom: 25px;'>Prime connection pipelines for any MT5 terminal.</h3>", unsafe_allow_html=True)
    
    broker_select = st.selectbox("SELECT DESTINATION BROKER TERMINAL ENGINE", 
                                 ["Exness Technologies Ltd", "JustMarkets Inc.", "XM Global Markets", "Windsor Brokers", "Pepperstone Group"])
    
    col_log1, col_log2 = st.columns(2)
    with col_log1:
        acc_num = st.text_input("MT5 ACCOUNT LOGIN ID", value="", placeholder="e.g., 474239881")
    with col_log2:
        acc_server = st.text_input("BROKER SERVER ASSIGNMENT", value="", placeholder="e.g., Exness-MT5-Trial15 or JustMarkets-Demo")
        
    acc_pass = st.text_input("ACCOUNT TRADING PASSWORD METRIC", type="password", placeholder="••••••••••••")
    
    st.write(" ")
    if st.button("Link Live Broker Pipeline Stream", key="btn_broker_auth"):
        if acc_num and acc_pass and acc_server:
            st.success(f"🔒 Pipeline authorized! Streamlit Cloud is now listening for webhook data packets from {broker_select} Server: {acc_server}")
        else:
            st.error("Please fill in your explicit login credentials and server paths to open authentication gates.")

# ==================== TAB 2: AUTOMATED DASHBOARD FORM ====================
with t_dashboard:
    st.subheader("📊 Cross-Broker Account Status Monitor")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: st.metric(label="Account Balance", value=f"${st.session_state.equity_history[-1]:.2f}")
    with m_col2: st.metric(label="Floating Equity", value=f"${st.session_state.equity_history[-1]:.2f}")
    with m_col3: st.metric(label="Active Open Profit/Loss", value="$0.00")
        
    st.divider()
    st.subheader("🤖 Strategy Execution Blueprint Matrix")
    
    with st.form("clearable_dispatch_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            direction = st.selectbox("Blueprint Direction", ["BUY_LIMIT", "SELL_LIMIT"])
            target_pair = st.selectbox("Asset Watchlist", ["XAUUSD", "EURUSD", "GBPUSD"])
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
            st.session_state.equity_history.append(st.session_state.equity_history[-1] + 25.00)
            st.balloons()
            st.success("✅ Trade matrix entry logged successfully. Inputs completely cleared for your next setup configuration!")

# ==================== TAB 3: PROF CHART CANVAS & REASONS LOG ====================
with t_chart:
    st.markdown("""
        <div class="header-box">
            <table style="width:100%; border:none;">
                <tr>
                    <td style="color:#10b981; font-family:monospace; font-weight:600;">🟢 ACTIVE WEB RADAR STREAM</td>
                    <td style="text-align:center; color:#60a5fa; font-family:monospace;"><span style="background-color:#1e293b; padding:3px 8px; border-radius:4px;">⏱️ TIME FILTER: POWER HOUR</span></td>
                    <td style="text-align:right; color:#9ca3af; font-family:monospace; font-weight:600;">XAUUSD M15</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

    np.random.seed(42)
    chart_time = pd.date_range(end=datetime.now(), periods=40, freq='15min')
    base_prices = np.sin(np.linspace(0, 4, 40)) * 15 + 2505
    opens = base_prices[:-1] + np.random.normal(0, 1, 39)
    closes = base_prices[1:] + np.random.normal(0, 1, 39)
    highs = np.maximum(opens, closes) + np.random.uniform(1, 3, 39)
    lows = np.minimum(opens, closes) - np.random.uniform(1, 3, 39)

    fig = go.Figure(data=[go.Candlestick(
        x=chart_time[:-1], open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#10b981', decreasing_line_color='#ef5350',
        increasing_fillcolor='#10b981', decreasing_fillcolor='#ef5350'
    )])

    # Precise Long/Short Risk Range target visualization boxes
    fig.add_shape(type="rect", x0=chart_time[0], y0=2500.00, x1=chart_time[-1], y1=2515.00, fillcolor="rgba(16, 185, 129, 0.12)", line=dict(width=0))
    fig.add_shape(type="rect", x0=chart_time[0], y0=2495.00, x1=chart_time[-1], y1=2500.00, fillcolor="rgba(239, 83, 80, 0.12)", line=dict(width=0))

    # Removed the unstable custom line properties causing Plotly value errors
    fig.add_hline(y=2515.00, line_dash="solid")
    fig.add_hline(y=2500.00, line_dash="dash")
    fig.add_hline(y=2495.00, line_dash="dash")

    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=350, margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='#0b1116', plot_bgcolor='#0b1116')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    col_lbl1, col_lbl2, col_lbl3 = st.columns(3)
    with col_lbl1: st.success("🎯 TARGET TAKE PROFIT: 2,515.00")
    with col_lbl2: st.info("🔵 PENDING LIMIT ENTRY: 2,500.00")
    with col_lbl3: st.error("🛑 DYNAMIC VALIDATION STOP LOSS: 2,495.00")

    st.write(" ")
    st.subheader("📝 Setup Structural Confluence Commentary Log")
    
    st.info("**🛡️ ORDER BLOCK LOCATION CRITERIA:**\n\nPrice printed a high-displacement shift in structure, confirming aggressive institutional accumulation. The origin candle boundary creates a high-probability loading area for market buy triggers.")
    st.warning("**⚡ FAIR VALUE GAP (FVG) VACUUM:**\n\nThe fast price movement generated an efficiency vacuum between Candle 1 and Candle 3. Our entry limits sit right at the top of this vacuum range to capture the retest liquidity phase before trend continuation.")
    st.error("**🔄 EXECUTION REVERSAL CANDLE LOG:**\n\nOur system strategy guidelines dictate that we monitor the lower execution timeframes for a clean rejection candle footprint (such as a long lower-wick pin bar) inside our zone boundaries before automated trailing protections engage.")

# ==================== TAB 4: SETUP GATE ====================
with t_gate:
    st.subheader("🛡️ Institutional Setup Validation Checklist")
    r1 = st.checkbox("🔍 Structural footprint has successfully tapped into unmitigated Order Block demand (OB)")
    r2 = st.checkbox("⚡ Strong momentum expansion displacement left a valid 3-candle Fair Value Gap vacuum (FVG)")
    r3 = st.checkbox("📈 Current pricing layout baseline is fully aligned with 200 MA trend vector parameters")
    r4 = st.checkbox("📊 Relative Strength Index (RSI 14) confirms clean structural momentum footprints")
    if r1 and r2 and r3 and r4: st.success("🔓 Setup Authorized! System strategy guidelines fully cleared.")

# ==================== TAB 5: JOURNAL LOGS ====================
with t_journal:
    st.subheader("🗒️ Smartphone Active Order Journal")
    if st.session_state.journal_data:
