import streamlit as st
import MetaTrader5 as mt5
import bot as trading_bot

st.set_page_config(page_title="Institutional Confluence Engine", layout="wide", page_icon="🦅")
st.title("🦅 Exness Automated Execution Workspace")

# Left Sidebar Controls
st.sidebar.header("🔐 Exness Account Authorization")
mt5_login = st.sidebar.number_input("MT5 Login ID Number", value=0, step=1)
mt5_password = st.sidebar.text_input("MT5 Account Trading Password", type="password")
mt5_server = st.sidebar.text_input("Exness Server Name", value="Exness-MT5-Trial15")

st.sidebar.header("Drawn Balance Configuration")
account_balance = st.sidebar.number_input("Account Balance ($)", value=500)
risk_pct = st.sidebar.slider("Risk Limit Per Setup (%)", 0.25, 2.0, 1.0, step=0.25)
target_pair = st.sidebar.selectbox("Select Watchlist Asset", ["XAUUSDm", "XAUUSD", "XAUUSD.", "EURUSD", "GBPUSD"])
session_filter = st.sidebar.selectbox("Enforce Session Timing Window", ["Disable Filter", "Power Hour", "London Breakout"])

# --- 1. LIVE ECONOMIC NEWS CALENDAR RADAR BLOCK ---
st.subheader("📰 Today's High-Impact Economic Radar")
try:
    news_events = trading_bot.fetch_economic_news()
    if news_events:
        for item in news_events[:3]:
            st.warning(f"🚨 **HIGH IMPACT NEWS ALERT:** {item.get('event')} ({item.get('currency')}) at {item.get('date')}. Volatility expected!")
    else:
        st.success("✅ Clean Fundamental Slate: No high-impact volatility drivers flagged for your watchlist currencies today.")
except Exception:
    st.info("ℹ️ News feed updating...")

st.divider()

# --- 2. STABILIZED ACCOUNT METRICS BLOCK ---
st.subheader("📊 Live Account Status Monitor")
metric_col1, metric_col2, metric_col3 = st.columns(3)

# Default placeholder values to keep the app interface from breaking if connection loops drop
live_bal = float(account_balance)
floating_equity = float(account_balance)
open_profit = 0.0
mt5_connected = False

# Try to connect securely to the running MT5 instance
if mt5_login > 0 and mt5_password:
    if trading_bot.initialize_mt5(mt5_login, mt5_password, mt5_server):
        acc_info = mt5.account_info()
        if acc_info is not None:
            live_bal = acc_info.balance
            floating_equity = acc_info.equity
            open_profit = acc_info.profit
            mt5_connected = True

# Safely render the metric display cards without blocking the execution inputs below
with metric_col1:
    st.metric(label="Live Account Balance", value=f"${round(live_bal, 2)}")
with metric_col2:
    st.metric(label="Floating Account Equity", value=f"${round(floating_equity, 2)}")
with metric_col3:
    st.metric(label="Active Open Profit/Loss", value=f"${round(open_profit, 2)}", 
              delta=f"${round(open_profit, 2)}" if open_profit != 0 else None)

if not mt5_connected:
    st.info("💡 Pro-Tip: Fill out your active MT5 authorization inputs on the left to sync live broker accounts.")

st.divider()

# --- 3. CORE TRADE PLACEMENT WORKSPACE PANEL ---
st.subheader("🤖 Precision Execution Workspace")
st.write("Extract coordinates using your TradingView position metrics and key them below:")
col1, col2, col3, col4 = st.columns(4)
with col1:
    direction = st.selectbox("Order Blueprint", ["BUY_LIMIT", "SELL_LIMIT"])
with col2:
    entry_level = st.number_input("Order Entry Target Price", value=0.0, format="%.5f")
with col3:
    sl_level = st.number_input("Stop Loss Target Level (Wick Edge)", value=0.0, format="%.5f")
with col4:
    tp_level = st.number_input("Take Profit Target Level", value=0.0, format="%.5f")

# Dynamic Pip Risk calculation math checks
recommended_lots = 0.01
if entry_level > 0 and sl_level > 0:
    pips_delta = abs(entry_level - sl_level)
    calculated_pips = pips_delta * 10000 if "USD" in target_pair else pips_delta * 10
    if "XAU" in target_pair:
        calculated_pips = pips_delta * 10 
        
    recommended_lots = trading_bot.calculate_position_size(live_bal, risk_pct, calculated_pips, target_pair)
    st.success(f"📊 Calculated Metric Output: Risking **${round(live_bal * (risk_pct/100), 2)}** | Stop Distance: **{round(calculated_pips, 1)} Pips** | Dynamic Lot Allocation: **{recommended_lots} Lots**")

# Execution Operations Handoff Sequence
if st.button("⚡ Dispatch Pending Order Matrix to Exness", type="primary"):
    if session_filter != "Disable Filter" and not trading_bot.is_within_dubai_window(session_filter):
        st.error(f"❌ Execution Blocked: Outside defined Dubai {session_filter} window. Stay flat outside high-volume sessions.")
    else:
        # Fallback authorization block if sidebar fields are left empty
        conn_ok = trading_bot.initialize_mt5(mt5_login, mt5_password, mt5_server) if mt5_login > 0 else trading_bot.initialize_mt5()
        if conn_ok:
            with st.spinner("Transmitting sequence metrics directly into market stream..."):
                receipt = trading_bot.send_limit_order(
                    symbol=target_pair, order_type=direction, entry_price=entry_level,
                    stop_loss=sl_level, take_profit=tp_level, lot_size=recommended_lots
                )
                if receipt["status"] == "SUCCESS":
                    st.balloons()
                    st.success(f"✅ Success! Pending Order accepted. Ticket ID: #{receipt['order_id']}")
                else:
                    st.error(f"❌ Transmission Rejection: {receipt['message']}")
        else:
            st.error("Failed to connect to MT5. Check your login details, server name, and confirm 'Algorithmic Trading' is active.")

# --- 4. DYNAMIC TRAILING PROTECTION MANAGER ---
st.divider()
st.subheader("🛡️ Intelligent Trade Protection Monitor")
trail_pips_input = st.slider("Define Dynamic Trailing Step Buffer (Pips)", min_value=10, max_value=100, value=20, step=5)

if st.button("🔄 Scan, Breakeven & Trail Active Open Positions"):
    conn_ok = trading_bot.initialize_mt5(mt5_login, mt5_password, mt5_server) if mt5_login > 0 else trading_bot.initialize_mt5()
    if conn_ok:
        with st.spinner("Analyzing open tickets..."):
            msg = trading_bot.manage_active_trades_with_trailing(trail_pips_input)
            st.info(msg)
    else:
        st.error("Cannot scan active open trades. Ensure MT5 is running and authorized.")
