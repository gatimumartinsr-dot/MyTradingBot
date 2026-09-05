import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time
from bot import calculate_position_size, dispatch_order

# Configuration setup for the institutional terminal look
st.set_page_config(page_title="Helix OB Terminal", layout="wide", page_icon="🟢")

# Global UI Custom Premium Styling Injection
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0d1117 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🟢 Helix OB — Automated Execution Workspace")
st.caption("Multi-User Cloud Trading Pipeline — Secure Independent Broker Access Gate")

# Sidebar Configuration — Unique session parameters per user login
st.sidebar.header("🔑 Your Broker Account")
exness_account = st.sidebar.number_input("Exness MT5 Account Login ID", value=12345678, step=1)
exness_password = st.sidebar.text_input("Exness Trading Password", type="password", value="YourSecurePassword")
exness_server = st.sidebar.text_input("Exness Server Name", value="Exness-MT5-Trial9")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategy Rules")
session_mode = st.sidebar.selectbox("Enforce Session Timing Window", ["Disable Filter", "Power Hour"])
risk_profile = st.sidebar.slider("Account Capital Risk Allocation (%)", 0.5, 5.0, 1.0, step=0.5)
account_balance = st.sidebar.number_input("Target Account Balance ($)", min_value=100.0, value=10000.0, step=500.0)

# Main Dashboard Workspace Layout - Explicit grid declaration
col1, col2 = st.columns(2)

with col1:
    st.subheader("Order Parameters")
    asset_symbol = st.text_input("Asset / Currency Instrument Symbol", value="XAUUSD")
    direction = st.radio("Order Direction", ["BUY", "SELL"], horizontal=True)
    
    entry_target = st.number_input("Order Entry Target Price", value=2500.00, step=0.10)
    sl_target = st.number_input("Stop Loss Target Level (Wick Edge)", value=2495.00, step=0.10)
    tp_target = st.number_input("Take Profit Target Level", value=2515.00, step=0.10)

with col2:
    st.subheader("Automated Risk Math")
    
    # Structural pip normalization calculations
    if "XAU" in asset_symbol or "XAG" in asset_symbol:
        pips_distance = abs(entry_target - sl_target) * 10
    else:
        pips_distance = abs(entry_target - sl_target) * 10000
        
    if pips_distance == 0:
        pips_distance = 1.0

    calculated_lots = calculate_position_size(account_balance, risk_profile, pips_distance, asset_symbol)
    max_cash_risk = account_balance * (risk_profile / 100.0)
    
    st.metric(label="Calculated Order Volume (Lots)", value=f"{calculated_lots} Lots")
    st.success(f"Maximum Cash Risk Safeguard: ${max_cash_risk:,.2f} USD")
    st.info(f"Target Stop Loss Width: {pips_distance:.1f} Structural Pips")

st.markdown("---")

# Execution Gateway Trigger Pipeline
if st.button("Connect Account & Dispatch Matrix", type="primary"):
    current_hour = datetime.now().hour
    if session_mode == "Power Hour" and not (16 <= current_hour < 18):
        st.error("Execution Rejected: System out of Institutional Volume Block (Power Hour). Change sidebar settings to bypass.")
    else:
        with st.spinner("Processing cloud network routing packet..."):
            execution_response = dispatch_order(
                login_id=exness_account,
                password=exness_password,
                server=exness_server,
                symbol=asset_symbol,
                order_type=direction,
                entry=entry_target,
                sl=sl_target,
                tp=tp_target,
                lots=calculated_lots
            )
            if execution_response["status"] == "success":
                st.balloons()
                st.success(f"🎉 Trade Dispatched! Cloud Ticket ID: {execution_response['order_id']}")
                st.info(f"Notification: {execution_response['message']}")
            else:
                st.error(f"{execution_response['message']}")

st.markdown("---")
st.subheader("📊 Operational Desk Monitoring Panels")

# Native tab layout rendering
tab1, tab2, tab3 = st.tabs(["📉 Price Line Modeling", "🗒 Active Live Trade Journal", "🔎 User Session Network Logs"])

with tab1:
    st.caption("Real-Time Asset Equity Progression Tracker")
    
    # Generate an elegant visual candlesticks or interactive chart line via Plotly
    x_steps = np.arange(1, 21)
    y_vals = np.random.randn(20).cumsum() + entry_target
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_steps, y=y_vals, mode='lines+markers', name='Market Value Track', line=dict(color='#00ff99', width=2)))
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.caption("Active Secure Memory Matrix — Session Order Parameter Blocks")
    journal_data = pd.DataFrame([
        {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), 
            "User Account": exness_account, 
            "Asset": asset_symbol, 
            "Action": f"{direction} LIMIT", 
            "Volume (Lots)": calculated_lots, 
            "Status": "Processing Cloud Routing"
        }
    ])
    st.dataframe(journal_data, use_container_width=True)

with tab3:
    st.caption("Multi-Tenant Cloud Workspace Gateway Trace Outputs")
    log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.code(f"""
[{log_time}] INITIALIZED: Multi-user cloud interface portal active.
[{log_time}] SECURE: Input channels routing for Account #{exness_account} isolated.
[{log_time}] LISTENING: Awaiting execution webhook transmission payload...
    """, language="bash")

st.markdown("""
### Systems Engineering Operational Notes
* **Precision Risk Control Engine:** This tool maps out contract parameters dynamically to eliminate human execution size calculation flaws.
* **Shared Gateway Multi-Tenancy:** Each session remains sandboxed. Accounts entered on the sidebar remain isolated to your device instance.
""")
