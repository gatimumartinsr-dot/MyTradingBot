import streamlit as st
import pandas as pd
import numpy as np
import random
import urllib.request
import json
from datetime import datetime

# ===================================================
# --- 👑 SYSTEM INITIALIZATION (MUST BE FIRST) -----
# ===================================================
st.set_page_config(page_title="Helix OB Global Portal", layout="wide", page_icon="🟢")

# Premium deep dark institutional custom theme wrapper injection
st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 15px !important; border-radius: 8px !important; border-left: 4px solid #00ff99 !important; } .stTabs [data-baseweb='tab-list'] { gap: 8px; } .stTabs [data-baseweb='tab'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 8px 16px !important; color: #8892b0 !important; border-radius: 4px 4px 0px 0px !important; } .stTabs [aria-selected='true'] { color: #00ff99 !important; border-bottom: 2px solid #00ff99 !important; } .stButton>button { border-radius: 6px !important; font-weight: 600 !important; } @media (max-width: 768px) { [data-testid='stSidebar'] { width: 100% !important; } }</style>", unsafe_allow_html=True)

# High-frequency multi-tenant session storage networks memory initialization
if "saas_user_db" not in st.session_state:
    st.session_state["saas_user_db"] = {"martins": "helix2026"}

if "saas_trades_db" not in st.session_state:
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["saas_trades_db"] = [
        {"Ticket": "TX-9931", "Asset": "XAUUSDm", "Type": "BUY LIMIT", "Lots": 0.01, "Entry": 2514.20, "PnL": "+$23.00"},
        {"Ticket": "TX-8824", "Asset": "BTCUSDm", "Type": "SELL LIMIT", "Lots": 0.05, "Entry": 56450.00, "PnL": "+$200.00"}
    ]

if "logged_in_status_flag" not in st.session_state: st.session_state["logged_in_status_flag"] = False
if "saas_auth_username" not in st.session_state: st.session_state["saas_auth_username"] = ""

# ===================================================
# --- 📁 BACKEND CORE SYSTEM ENGINE CONTROLLERS ----
# ===================================================

# 📬 ENTERPRISE WEBHOOK INTERCEPTOR PROTOCOL
def transmit_outbound_webhook(payload, target_url=""):
    """
    Dispatches zero-dependency secure POST network streams to alert channels
    """
    if not target_url or not target_url.startswith("http"):
        return False  # Prevents thread freezing if URL is missing
    try:
        # Build clean structural JSON message block
        message_body = {
            "content": f"🚨 **HELIX INTEL DISPATCH GATEWAY** 🚨\n"
                       f"• **Operator Node:** `{payload['user'].upper()}`\n"
                       f"• **Transaction Ticket:** `{payload['ticket']}`\n"
                       f"• **Asset Focus:** `{payload['asset']}`\n"
                       f"• **Execution Vector:** `{payload['type']}`\n"
                       f"• **Position Volume:** `{payload['lots']} Lots`\n"
                       f"• **Target Entry Price:** `${payload['entry']:,.2f}`\n"
                       f"• **Time Stamp Matrix:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        }
        json_data = json.dumps(message_body).encode("utf-8")
        req = urllib.request.Request(
            target_url, 
            data=json_data, 
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in [200, 204]
    except Exception:
        return False

# ===================================================
# --- 🖥️ FRONTEND USER INTERFACE LAYOUT LAYER ------
# ===================================================
if not st.session_state["logged_in_status_flag"]:
    st.markdown("<h1 style='text-align: center; color: #00ff99; margin-top: 40px;'>🟢 HELIX OB GLOBAL PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8892b0;'>Multi-Tenant Standalone Algorithmic Workstation</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    _, auth_col, _ = st.columns([1, 1.5, 1])
    with auth_col:
        gate_mode = st.radio("Access Control Mode", ["Sign In to Account", "Create Standalone Account"], horizontal=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        user_input = st.text_input("Username Identifier Key", key="user_field_v11").strip().lower()
        pass_input = st.text_input("Access Password", type="password", key="pass_field_v11").strip()
        
        if gate_mode == "Sign In to Account":
            if st.button("Authorize Connection Session", type="primary", use_container_width=True):
                if st.session_state["saas_user_db"].get(user_input) == pass_input:
                    st.session_state["logged_in_status_flag"] = True
                    st.session_state["saas_auth_username"] = user_input
                    st.rerun()
                else:
                    st.error("Invalid credentials or unregistered operator profile key.")
        else:
            if st.button("Generate Standalone Credentials", type="primary", use_container_width=True):
                if user_input and pass_input:
                    if user_input in st.session_state["saas_user_db"]:
                        st.error("Username key is already taken.")
                    else:
                        st.session_state["saas_user_db"][user_input] = pass_input
                        st.success("Account profile compiled successfully! Please select 'Sign In' to connect.")
                else:
                    st.warning("Please specify valid characters.")
else:
    current_user = st.session_state["saas_auth_username"]
    st.markdown(f"<div style='float: right; color: #8892b0; font-family: monospace;'>User Context: <b>{current_user.upper()}</b></div>", unsafe_allow_html=True)
    st.title("🟢 Helix Automated Trading Desk")
    st.markdown("---")
    
    # --- SIDEBAR CONTROL PARAMETERS ---
    st.sidebar.header("Market Asset Settings")
    symbol_choice = st.sidebar.selectbox("Tracked Target Instrument", ["XAUUSDm", "BTCUSDm", "EURUSDm"])
    
    account_balance = st.sidebar.number_input("Target Account Balance ($)", value=161.53)
    risk_percentage = st.sidebar.slider("Account Capital Exposure Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    
    st.sidebar.markdown("---")
    st.sidebar.header("📬 Live Alert Routing")
    webhook_url_input = st.sidebar.text_input(
        "Target Webhook URL String", 
        value="", 
        placeholder="https://discord.com...",
        help="Paste your Discord or Telegram bot URL address endpoint to route automated logs instantly."
    )

    # --- METRIC PANELS ---
    m_c1, m_c2, m_c3 = st.columns(3)
    m_c1.metric(label="ACCOUNT BALANCE CONTEXT", value=f"${account_balance:,.2f}")
    m_c2.metric(label="TRACKED ASSET FOCUS", value=str(symbol_choice))
    m_c3.metric(label="RISK ALLOCATION SAFEGUARD", value=f"{risk_percentage}% Layer")
    
    tab_desk, tab_journal = st.tabs(["Live Trading Desk", "Personal Journal Logs"])
    
    with tab_desk:
        st.markdown("<br>### Live Open Position Matrix Grid", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(st.session_state["saas_trades_db"]), use_container_width=True, hide_index=True)
        
        st.markdown("<br>### Manual Order Dispatch Gateway Router", unsafe_allow_html=True)
        o_c1, o_c2 = st.columns(2)
        direction = o_c1.radio("Transaction Vector Direction", ["BUY LIMIT", "SELL LIMIT"], horizontal=True)
        entry_input = o_c2.number_input("Target Entry Price", value=2515.20 if "XAU" in symbol_choice else 56420.00)
        
        if st.button("🚀 TRANSMIT ORDER MATRIX TO MT5 LIVE NODE", type="primary", use_container_width=True):
            assigned_ticket = f"TX-{random.randint(50000, 99999)}"
            new_row = {"Ticket": assigned_ticket, "Asset": symbol_choice, "Type": direction, "Lots": 0.01, "Entry": entry_input, "PnL": "+$0.00"}
            
            # Update background memory array
            st.session_state["saas_trades_db"].append(new_row)
            
            # Fire outward notification if URL endpoint is defined
            if webhook_url_input:
                webhook_payload = {
                    "user": current_user,
                    "ticket": assigned_ticket,
                    "asset": symbol_choice,
                    "type": direction,
                    "lots": 0.01,
                    "entry": entry_input
                }
                with st.spinner("Streaming data packets to webhook channel..."):
                    stream_pass = transmit_outbound_webhook(webhook_payload, webhook_url_input)
                if stream_pass:
                    st.toast("📬 Telemetry transmitted successfully to destination network node!", icon="✅")
                else:
                    st.toast("⚠️ Webhook connection timeout. Ledger updated locally.", icon="⚠️")
                    
            st.success("Trade successfully routed to demo broker stream node!")
            st.rerun()
            
    with tab_journal:
        st.markdown("### Historical Multi-Symbol Trade Archive Logs")
        st.dataframe(pd.DataFrame(st.session_state["saas_trades_db"]), use_container_width=True, hide_index=True)
        if st.button("🔒 SEVER PROFILE CONNECTION AND LOG OUT", type="secondary", use_container_width=True):
            st.session_state["logged_in_status_flag"] = False
            st.session_state["saas_auth_username"] = ""
            st.rerun()
