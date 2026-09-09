import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime

# 1. Page Configuration MUST occur at the absolute top trace line
st.set_page_config(page_title="Helix OB Global Portal", layout="wide", page_icon="🟢")

# 2. Hard-Sealed Session State Storage Initializer Matrix
if "logged_in_status_flag" not in st.session_state:
    st.session_state["logged_in_status_flag"] = False
if "saas_auth_username" not in st.session_state:
    st.session_state["saas_auth_username"] = ""

# Mock Databases
if "saas_user_db" not in st.session_state:
    st.session_state["saas_user_db"] = {"martins": "helix2026"}
if "saas_trades_db" not in st.session_state:
    st.session_state["saas_trades_db"] = [
        {"Ticket": "TX-9931", "Asset": "XAUUSDm", "Type": "BUY LIMIT", "Lots": 0.01, "Entry": 2514.20, "PnL": "+$23.00"},
        {"Ticket": "TX-8824", "Asset": "BTCUSDm", "Type": "SELL LIMIT", "Lots": 0.05, "Entry": 56450.00, "PnL": "+$200.00"}
    ]

# Custom Institutional CSS styling parameters
st.markdown("<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] { background-color: #0b0e14 !important; color: #e1e4ea !important; } div[data-testid='metric-container'] { background-color: #121620 !important; border: 1px solid #1f2433 !important; padding: 15px !important; border-radius: 8px !important; border-left: 4px solid #00ff99 !important; }</style>", unsafe_allow_html=True)

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
        
        user_input = st.text_input("Username Identifier Key", key="user_field_v10").strip().lower()
        pass_input = st.text_input("Access Password", type="password", key="pass_field_v10").strip()
        
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
    
    st.sidebar.header("Market Asset Settings")
    symbol_choice = st.sidebar.selectbox("Tracked Target Instrument", ["XAUUSDm", "BTCUSDm", "EURUSDm"])
    
    account_balance = st.sidebar.number_input("Target Account Balance ($)", value=161.53)
    risk_percentage = st.sidebar.slider("Account Capital Exposure Risk (%)", 1.0, 10.0, 2.0, step=0.5)
    
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
            new_row = {"Ticket": f"TX-{random.randint(50000, 99999)}", "Asset": symbol_choice, "Type": direction, "Lots": 0.01, "Entry": entry_input, "PnL": "+$0.00"}
            st.session_state["saas_trades_db"].append(new_row)
            st.success("Trade successfully routed to demo broker stream node!")
            st.rerun()
            
    with tab_journal:
        st.markdown("### Historical Multi-Symbol Trade Archive Logs")
        st.dataframe(pd.DataFrame(st.session_state["saas_trades_db"]), use_container_width=True, hide_index=True)
        if st.button("🔒 SEVER PROFILE CONNECTION AND LOG OUT", type="secondary", use_container_width=True):
            st.session_state["logged_in_status_flag"] = False
            st.session_state["saas_auth_username"] = ""
            st.rerun()
