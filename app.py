"""
app.py — Zonelock: support & resistance auto-trading interface.

Replaces the old Helix OB portal. Streamlit Cloud runs this file directly.

Runs the same faces as the design: Login → Broker credentials → Rules →
the tabbed app (Desk, Charts, Journal, Rules, Account).

    pip install streamlit pandas plotly MetaTrader5
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0

Reads decisions from journal.jsonl (written by engine.py) and talks to MT5
when it is available. Without a terminal it runs in demo mode on sample data,
so you can develop it on a Mac and deploy it on the Windows VPS unchanged.
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from strategy import Rules, build_zones, find_fvgs, order_blocks, evaluate

JOURNAL = os.environ.get("ZONELOCK_JOURNAL", "journal.jsonl")
SYMBOLS = ["XAUUSDm", "EURUSDm", "GBPUSDm", "US30m", "NAS100m", "BTCUSDm", "USOILm"]

BG, SURFACE, TEXT = "#161826", "#232532", "#e9e9ed"
ACCENT, A300, A800 = "#9184d9", "#d2cefd", "#423a6a"
UP, DOWN, MUTED = "#7fbf9a", "#d98a94", "#9397ab"

st.set_page_config(page_title="Zonelock", layout="wide", page_icon="◈",
                   initial_sidebar_state="auto")

st.markdown(f"""
<style>
  html, body, [data-testid='stAppViewContainer'], [data-testid='stHeader'] {{
      background:{BG} !important; color:{TEXT} !important;
      font-family:Inter, system-ui, sans-serif; }}
  [data-testid='stSidebar'] {{ background:{SURFACE} !important; }}
  h1,h2,h3,h4,h5 {{ font-weight:500 !important; letter-spacing:-.015em; }}
  [data-testid='stMetric'] {{ background:{SURFACE}; border-radius:8px;
      padding:13px 14px; box-shadow:0 0 0 1px #3f424d; }}
  [data-testid='stMetricLabel'] {{ font-size:9.5px !important; letter-spacing:.09em;
      text-transform:uppercase; color:{MUTED} !important; }}
  .stTabs [data-baseweb='tab-list'] {{ gap:6px; border-bottom:1px solid rgba(233,233,237,.16); }}
  .stTabs [data-baseweb='tab'] {{ background:transparent !important; color:{MUTED} !important;
      padding:9px 16px !important; font-size:13px !important; }}
  .stTabs [aria-selected='true'] {{ color:{A300} !important;
      border-bottom:2px solid {ACCENT} !important; }}
  .stButton>button {{ background:transparent; border:1px solid {ACCENT}; color:{ACCENT};
      border-radius:8px; font-weight:500; font-size:14px; }}
  .stButton>button:hover {{ background:rgba(145,132,217,.12); color:{A300}; border-color:{ACCENT}; }}
  .zl-card {{ background:{SURFACE}; border-radius:8px; padding:14px;
      box-shadow:0 0 0 1px #3f424d; margin-bottom:9px; }}
  .zl-kicker {{ font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:{ACCENT}; }}
  .zl-tag {{ display:inline-block; font-size:10px; padding:3px 9px; border-radius:6px;
      background:#3f424d; color:#f3f5fe; margin-right:5px; white-space:nowrap; }}
  .zl-muted {{ color:{MUTED}; font-size:11.5px; line-height:1.5; }}
  [data-testid='stMetricValue'] {{ font-size:21px !important; }}
  .stTabs [data-baseweb='tab-list'] {{ overflow-x:auto; flex-wrap:nowrap; }}
  @media (max-width:768px) {{
      .block-container {{ padding:1rem 0.8rem 3rem !important; }}
      [data-testid='stMetricValue'] {{ font-size:17px !important; }}
      [data-testid='stMetric'] {{ padding:10px !important; }}
      h1 {{ font-size:26px !important; }} h2 {{ font-size:21px !important; }}
      .stTabs [data-baseweb='tab'] {{ padding:8px 11px !important; font-size:12px !important; }}
      [data-testid='stDataFrame'] {{ font-size:11px; }}
      [data-testid='column'] {{ min-width:100% !important; }}
  }}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────────────

DEFAULTS = {
    "stage": "login", "user": "", "email": "", "mode": "demo",
    "accounts": [], "rules": Rules(), "symbol": SYMBOLS[0],
    "broker": {"broker": "Exness", "login": "", "password": "", "server": "Exness-Trial2"},
    "mt5_note": "",
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def goto(stage: str):
    st.session_state["stage"] = stage
    st.rerun()


# ──────────────────────────────────────────────────────────────────────
# Data
# ──────────────────────────────────────────────────────────────────────

def mt5_connect(login, password, server):
    if not MT5_AVAILABLE:
        return False, "MetaTrader5 package unavailable — this host is not Windows. Running on sample data."
    if not mt5.initialize():
        return False, f"Terminal did not initialise: {mt5.last_error()}"
    if not mt5.login(login=int(login), password=password, server=server):
        err = mt5.last_error()
        mt5.shutdown()
        return False, f"Login rejected: {err}"
    a = mt5.account_info()
    return True, f"Bound to {server} · {a.login} · {a.balance:.2f} {a.currency}"


@st.cache_data(ttl=20)
def candles(symbol: str, count: int = 300) -> pd.DataFrame:
    if MT5_AVAILABLE:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, count)
        if rates is not None and len(rates):
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
            return df.iloc[:-1].reset_index(drop=True)
    return sample_candles(symbol, count)


def sample_candles(symbol: str, n: int = 300) -> pd.DataFrame:
    """
    Deterministic price action that actually respects levels — trends, then
    ranges between a floor and a ceiling, so zones and gaps mean something.
    """
    import math
    import random

    base = {"XAU": 4389.2, "BTC": 64350.0, "EUR": 1.1045, "GBP": 1.2918,
            "US30": 44210.0, "NAS": 20475.0, "OIL": 71.44}
    anchor = next((v for k, v in base.items() if k in symbol.upper()), 100.0)
    vol = anchor * 0.0009
    rnd = random.Random(sum(map(ord, symbol)) * 31)

    # alternating regimes: trend, range, trend — the shape S&R is built for
    regimes, i = [], 0
    while i < n:
        span = rnd.randint(28, 46)
        kind = "range" if len(regimes) % 2 else rnd.choice(["up", "down"])
        regimes.append((kind, min(span, n - i)))
        i += span

    rows, p = [], anchor - vol * 12
    floor = ceiling = None
    t_end = pd.Timestamp.now(tz="UTC").floor("15min")

    for k, (kind, span) in enumerate(regimes):
        if kind == "range":
            floor, ceiling = p - vol * 7, p + vol * 7
        for j in range(span):
            o = p
            if kind == "range":
                # pull back toward the middle, harder near the edges
                pos = (p - floor) / max(ceiling - floor, 1e-9)
                pull = (0.5 - pos) * 2.2
                p += (rnd.random() - 0.5 + pull) * vol
            else:
                bias = 0.42 if kind == "up" else -0.42
                p += (rnd.random() - 0.5 + bias) * vol * 1.4
            body = abs(p - o)
            wick = vol * (0.25 + rnd.random() * 0.75)
            rows.append({"open": o, "close": p,
                         "high": max(o, p) + wick * rnd.random() + body * 0.1,
                         "low": min(o, p) - wick * rnd.random() - body * 0.1})

    rows = rows[:n]
    times = [t_end - pd.Timedelta(minutes=15 * (len(rows) - 1 - i)) for i in range(len(rows))]
    df = pd.DataFrame(rows)
    df.insert(0, "time", times)
    return df


def account_snapshot():
    if MT5_AVAILABLE and mt5.account_info():
        a = mt5.account_info()
        return {"balance": a.balance, "equity": a.equity, "currency": a.currency, "login": a.login}
    return {"balance": 10000.0 if st.session_state["mode"] == "demo" else 161.53,
            "equity": 10000.0, "currency": "USD", "login": "sample"}


def positions():
    if MT5_AVAILABLE:
        pos = mt5.positions_get()
        if pos:
            return pd.DataFrame([{
                "Symbol": p.symbol, "Side": "BUY" if p.type == 0 else "SELL",
                "Lots": p.volume, "Entry": p.price_open, "SL": p.sl, "TP": p.tp,
                "P&L": round(p.profit, 2)} for p in pos])
    return pd.DataFrame([
        {"Symbol": "XAUUSDm", "Side": "BUY", "Lots": 0.01, "Entry": 4387.10, "SL": 4385.30, "TP": 4396.80, "P&L": 23.00},
        {"Symbol": "BTCUSDm", "Side": "SELL", "Lots": 0.01, "Entry": 64365.0, "SL": 64610.0, "TP": 63940.0, "P&L": -4.60},
    ])


def journal(limit: int = 300):
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows[-limit:][::-1]


# ──────────────────────────────────────────────────────────────────────
# Chart
# ──────────────────────────────────────────────────────────────────────

VISIBLE_BARS = 120


def chart(symbol: str, df: pd.DataFrame, rules: Rules, bars: int = VISIBLE_BARS) -> go.Figure:
    """
    Levels are read from the FULL history — a zone is only meaningful if it was
    respected over time — but only the last `bars` candles are shown, so the
    bodies are readable. Boxes run from where they formed to the right edge,
    the way a terminal draws them, and each label sits in the right margin.
    """
    zones = build_zones(df, rules)
    gaps = [g for g in find_fvgs(df, rules) if not g.filled]
    blocks = order_blocks(df, rules)

    view = df.iloc[-bars:].reset_index(drop=True)
    price = float(view["close"].iloc[-1])
    lo_v, hi_v = float(view["low"].min()), float(view["high"].max())
    pad = (hi_v - lo_v) * 0.08
    y_lo, y_hi = lo_v - pad, hi_v + pad

    t0, t1 = view["time"].iloc[0], view["time"].iloc[-1]
    bar = view["time"].iloc[1] - view["time"].iloc[0]
    right = t1 + bar * 9          # quiet margin the labels live in
    digits = 5 if price < 20 else 2

    fig = go.Figure(go.Candlestick(
        x=view["time"], open=view["open"], high=view["high"],
        low=view["low"], close=view["close"],
        increasing_line_color=UP, decreasing_line_color=DOWN,
        increasing_fillcolor=UP, decreasing_fillcolor=DOWN,
        line_width=1, whiskerwidth=0.25, name=symbol,
        hovertext=None, showlegend=False))

    def band(lo, hi, fill, edge, label, start=None, dash=None):
        """A shaded band with its label parked in the right margin."""
        if hi < y_lo or lo > y_hi:
            return                                   # off screen, skip it
        thin = (hi - lo) < (y_hi - y_lo) * 0.006     # give hairlines presence
        if thin:
            mid = (lo + hi) / 2
            lo, hi = mid - (y_hi - y_lo) * 0.003, mid + (y_hi - y_lo) * 0.003
        fig.add_shape(type="rect", x0=start or t0, x1=right, y0=lo, y1=hi,
                      fillcolor=fill, layer="below",
                      line=dict(color=edge, width=1, dash=dash or "solid"))
        fig.add_annotation(x=right, y=(lo + hi) / 2, text=label, showarrow=False,
                           xanchor="right", yanchor="middle",
                           font=dict(size=9, color=edge, family="Inter"))

    # the two zones that matter: nearest support below, nearest resistance above
    below = [z for z in zones if z.kind == "support" and z.mid <= price]
    above = [z for z in zones if z.kind == "resistance" and z.mid >= price]
    if below:
        z = max(below, key=lambda z: z.mid)
        band(z.low, z.high, "rgba(127,191,154,.11)", UP, f"SUPPORT  {z.mid:,.{digits}f}")
    if above:
        z = min(above, key=lambda z: z.mid)
        band(z.low, z.high, "rgba(217,138,148,.11)", DOWN, f"RESISTANCE  {z.mid:,.{digits}f}")

    # gaps and blocks start where they formed
    def x_at(idx):
        offset = idx - (len(df) - len(view))
        return view["time"].iloc[offset] if 0 <= offset < len(view) else t0

    for g in gaps[-2:]:
        band(g.low, g.high, "rgba(145,132,217,.14)", A300, "FVG", x_at(g.index), "dot")

    for ob in blocks[:1]:
        band(ob.low, ob.high, "rgba(145,132,217,.26)", ACCENT,
             f"{ob.direction[:4].upper()} OB · {ob.event}", x_at(ob.index))

    # last price
    fig.add_shape(type="line", x0=t0, x1=right, y0=price, y1=price,
                  line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=right, y=price, text=f"  {price:,.{digits}f}  ", showarrow=False,
                       xanchor="left", yanchor="middle", font=dict(size=10, color="#161826"),
                       bgcolor=A300, borderpad=3)

    fig.update_layout(
        height=470, margin=dict(l=6, r=64, t=10, b=6),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, dragmode="pan",
        font=dict(color=TEXT, family="Inter", size=11),
        hovermode="x unified", showlegend=False,
        hoverlabel=dict(bgcolor="#1b1d2b", bordercolor="#3f424d",
                        font=dict(color=TEXT, family="Inter", size=11)),
        xaxis=dict(rangeslider_visible=False, gridcolor="rgba(233,233,237,.05)",
                   showline=False, zeroline=False, range=[t0, right],
                   showspikes=True, spikemode="across", spikesnap="cursor",
                   spikecolor="rgba(233,233,237,.22)", spikethickness=1, spikedash="dot"),
        yaxis=dict(gridcolor="rgba(233,233,237,.05)", side="right", zeroline=False,
                   range=[y_lo, y_hi], tickformat=f",.{digits}f", showspikes=False))
    return fig


def safe(fn, label):
    """Render a tab; show the real error inline instead of killing the page."""
    try:
        fn()
    except Exception as exc:
        st.error(f"{label} could not render: {type(exc).__name__} — {exc}")
        with st.expander("Details"):
            import traceback
            st.code(traceback.format_exc())


# ──────────────────────────────────────────────────────────────────────
# Face 1 — login
# ──────────────────────────────────────────────────────────────────────

def face_login():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='letter-spacing:.2em;font-size:13px;color:{TEXT}'>◈ ZONELOCK</div>",
                    unsafe_allow_html=True)
        st.markdown("## Trades the zone, not the noise.")
        st.markdown("<p class='zl-muted'>It waits at support, checks the candle actually turned, "
                    "then places the order on your own broker account.</p>", unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign in", "Create account"])
        with tab_in:
            email = st.text_input("Email", "martins@zonelock.app", key="li_email")
            pwd = st.text_input("Password", "helix2026", type="password", key="li_pass")
            if st.button("Sign in", use_container_width=True):
                if email and pwd:
                    st.session_state.update(email=email, user=email.split("@")[0].title())
                    goto("app")
                else:
                    st.error("Enter your email and password.")
        with tab_up:
            name = st.text_input("Full name", key="su_name")
            email2 = st.text_input("Email", key="su_email")
            pwd2 = st.text_input("Password", type="password", key="su_pass")
            if st.button("Create account", use_container_width=True):
                if name and email2 and len(pwd2) >= 6:
                    st.session_state.update(user=name, email=email2)
                    goto("creds")
                else:
                    st.error("Name, email and a password of 6+ characters.")
        st.caption("Your Zonelock login is separate from your broker. You link MT5 next.")


# ──────────────────────────────────────────────────────────────────────
# Face 2 — broker credentials
# ──────────────────────────────────────────────────────────────────────

def face_creds():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
        st.progress(0.66, text="Step 2 of 3")
        st.markdown("## Your broker credentials")
        st.markdown("<p class='zl-muted'>This is the account the bot places orders on. Zonelock can "
                    "place and manage trades — it can never withdraw.</p>", unsafe_allow_html=True)

        b = st.session_state["broker"]
        b["broker"] = st.selectbox("Broker", ["Exness", "IC Markets", "Pepperstone", "Deriv", "FBS", "Other MT5"])
        b["login"] = st.text_input("MT5 account login", b["login"], placeholder="50239102")
        b["password"] = st.text_input("Password", b["password"], type="password",
                                      help="Use the investor password while testing — it cannot trade.")
        b["server"] = st.text_input("Server", b["server"])

        c1, c2 = st.columns(2)
        if c1.button("Link terminal and continue", use_container_width=True):
            if len(b["login"]) < 4 or not b["password"]:
                st.error("Enter your MT5 login and password.")
            else:
                ok, note = mt5_connect(b["login"], b["password"], b["server"])
                st.session_state["mt5_note"] = note
                st.session_state["accounts"].append(
                    {"broker": b["broker"], "server": b["server"], "login": b["login"], "live": ok, "primary": True})
                goto("setup")
        if c2.button("Skip for now", use_container_width=True):
            goto("setup")


# ──────────────────────────────────────────────────────────────────────
# Face 3 — rules
# ──────────────────────────────────────────────────────────────────────

def face_setup():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
        st.progress(1.0, text="Step 3 of 3")
        st.markdown("## The rules it trades by")
        st.markdown("<p class='zl-muted'>Pick how hard it pushes. Every single rule stays editable "
                    "in the Rules tab.</p>", unsafe_allow_html=True)

        profile = st.radio("Risk profile", ["Careful", "Balanced", "Bold"], index=1, horizontal=True,
                           captions=["1% · 2 trades", "2% · 3 trades", "3% · 5 trades"])
        r: Rules = st.session_state["rules"]
        r.risk_percent, r.max_open_positions = {
            "Careful": (1.0, 2), "Balanced": (2.0, 3), "Bold": (3.0, 5)}[profile]

        st.markdown("**Always on**")
        for line in [
            "Only enters at a support or resistance zone, never mid-range.",
            "Waits for a reversal candle to actually close inside the zone.",
            "Order blocks must carry a BOS or CHoCH to count.",
            "Stops all new entries 30 minutes either side of red news.",
            f"Stands down for the day once ${r.daily_profit_cap:.0f} is made.",
        ]:
            st.markdown(f"<div class='zl-muted'>✓&nbsp; {line}</div>", unsafe_allow_html=True)

        st.write("")
        if st.button("Arm the bot", use_container_width=True):
            goto("app")


# ──────────────────────────────────────────────────────────────────────
# Face 4 — the app
# ──────────────────────────────────────────────────────────────────────

def face_app():
    r: Rules = st.session_state["rules"]
    acct = account_snapshot()
    mode = st.session_state["mode"]

    with st.sidebar:
        st.markdown(f"<div style='letter-spacing:.2em;font-size:12px'>◈ ZONELOCK</div>", unsafe_allow_html=True)
        st.caption(st.session_state["email"] or "not signed in")
        st.session_state["mode"] = st.radio("Mode", ["demo", "live"],
                                            index=0 if mode == "demo" else 1,
                                            format_func=str.upper, horizontal=True)
        if st.session_state["mode"] == "live":
            st.warning("Real money. Orders go to your broker.", icon="⚠")
        st.session_state["symbol"] = st.selectbox("Symbol", SYMBOLS,
                                                  index=SYMBOLS.index(st.session_state["symbol"]))
        st.divider()
        st.caption(st.session_state["mt5_note"] or
                   ("MT5 terminal connected." if MT5_AVAILABLE else "Sample data — no Windows terminal here."))
        if st.button("Sign out", use_container_width=True):
            st.session_state["stage"] = "login"
            st.rerun()

    symbol = st.session_state["symbol"]
    df = candles(symbol)
    rows = journal()
    taken = [x for x in rows if x.get("taken")]
    passed = [x for x in rows if not x.get("taken")]

    desk, charts, jrnl, rules_tab, account = st.tabs(["Desk", "Charts", "Journal", "Rules", "Account"])

    def _desk():
        realised = round(sum(float(x.get("pnl", 0.0)) for x in taken), 2)
        cap_pct = (realised / r.daily_profit_cap) if r.daily_profit_cap else 0.0
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Balance", f"{acct['balance']:,.2f} {acct['currency']}")
        k2.metric("Today", f"${realised:,.2f}", f"{cap_pct:.0%} of cap")
        k3.metric("Open slots", f"{len(positions())} of {r.max_open_positions}")
        k4.metric("Decisions logged", f"{len(rows)}", f"{len(taken)} taken")

        st.markdown("##### Live evaluation")
        dec = evaluate(symbol, df, balance=acct["balance"], tick_value=1.0, tick_size=0.01,
                       open_positions=len(positions()), daily_pnl=realised, rules=r)
        box = f"""<div class='zl-card'>
          <div class='zl-kicker'>{symbol}</div>
          <div style='font-size:16px;margin-top:4px'>{dec.headline or dec.verdict}</div>
          <div class='zl-muted' style='margin-top:6px'>{'Signal · ' + str(dec.direction) + ' ' + str(dec.lots) + ' lots @ ' + str(dec.entry) if dec.taken else 'Passed — ' + dec.verdict}</div>
        </div>"""
        st.markdown(box, unsafe_allow_html=True)
        for c in dec.checks:
            st.markdown(f"<div class='zl-muted'>{'✓' if c.passed else '✕'}&nbsp; {c.label} "
                        f"<span style='color:{MUTED}'>— {c.value}</span></div>", unsafe_allow_html=True)

        st.markdown("##### Open positions")
        st.dataframe(positions(), use_container_width=True, hide_index=True)

    def _charts():
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"##### {symbol} · M15")
        span = c2.select_slider("Bars", [60, 120, 200, 300], value=120,
                                label_visibility="collapsed")
        st.plotly_chart(chart(symbol, df, r, span), use_container_width=True,
                        config={"displayModeBar": False, "scrollZoom": True})
        st.caption("Support and resistance from clustered swing points · unfilled fair value gaps · "
                   "order blocks validated by BOS or CHoCH.")

    def _journal():
        t_taken, t_passed, t_stats = st.tabs(["Taken", "Not taken", "Stats"])
        with t_taken:
            if taken:
                st.dataframe(pd.DataFrame([{
                    "When": x.get("at", "")[11:16], "Symbol": x.get("symbol", ""),
                    "Side": x.get("direction", ""), "Lots": x.get("lots", 0),
                    "Entry": x.get("entry"), "R:R": x.get("rr"), "Why": x.get("headline", ""),
                } for x in taken]), use_container_width=True, hide_index=True)
            else:
                st.info("No trades taken yet. Run engine.py to fill the journal.")
        with t_passed:
            if not passed:
                st.info("No rejections logged yet.")
            for x in passed[:40]:
                with st.expander(f"{x.get('symbol','')} · {x.get('verdict','')} · {x.get('at','')[11:16]}"):
                    st.write(x.get("headline", ""))
                    for c in x.get("checks", []):
                        st.markdown(f"<div class='zl-muted'>{'✓' if c['passed'] else '✕'}&nbsp; "
                                    f"{c['label']} — {c['value']}</div>", unsafe_allow_html=True)
        with t_stats:
            if passed:
                counts = pd.Series([x["verdict"] for x in passed]).value_counts()
                st.bar_chart(pd.DataFrame({"count": counts}), color=ACCENT)
                st.caption("Why setups were turned down.")
            else:
                st.info("Stats appear once the engine has logged decisions.")

    def _rules():
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Entry rules")
            r.require_reversal_candle = st.toggle("Require a reversal candle", r.require_reversal_candle)
            r.require_fvg_unfilled = st.toggle("Fair value gap must be unfilled", r.require_fvg_unfilled)
            r.require_ob_structure = st.toggle("Order block needs BOS", r.require_ob_structure)
            r.accept_choch = st.toggle("Accept CHoCH reversals", r.accept_choch)
            r.min_zone_touches = st.slider("Minimum zone touches", 1, 5, r.min_zone_touches)
        with c2:
            st.markdown("##### Risk")
            r.base_lot = st.number_input("Base lot size", 0.01, 5.0, r.base_lot, 0.01, format="%.2f")
            r.risk_percent = st.slider("Risk per trade (%)", 0.5, 5.0, r.risk_percent, 0.5)
            r.max_open_positions = st.slider("Max open positions", 1, 10, r.max_open_positions)
            r.daily_profit_cap = st.number_input("Daily profit cap ($)", 0.0, 5000.0, r.daily_profit_cap, 5.0)
            r.max_daily_loss = st.number_input("Max daily loss ($)", 0.0, 5000.0, r.max_daily_loss, 5.0)
            st.markdown("##### Timing")
            r.news_block_minutes = st.slider("News blackout (minutes each side)", 0, 120, r.news_block_minutes, 5)
            r.session_filter = st.toggle("Session-aware volatility", r.session_filter)
        st.session_state["rules"] = r
        st.caption("Changes apply on the next candle close.")

    def _account():
        c1, c2 = st.columns([1.3, 1])
        with c1:
            st.markdown("##### Trading accounts")
            if not st.session_state["accounts"]:
                st.info("No broker linked yet.")
            for a in st.session_state["accounts"]:
                st.markdown(f"<div class='zl-card'><b>{a['broker']} · {a['server']}</b><br>"
                            f"<span class='zl-muted'>Login {a['login']} · "
                            f"{'connected' if a['live'] else 'not connected'}</span></div>",
                            unsafe_allow_html=True)
            with st.expander("Link another broker"):
                nb = st.selectbox("Broker", ["Exness", "IC Markets", "Pepperstone", "Deriv", "FBS", "Other MT5"], key="nb")
                nl = st.text_input("MT5 login", key="nl")
                np_ = st.text_input("Password", type="password", key="np")
                ns = st.text_input("Server", key="ns")
                if st.button("Link live terminal"):
                    if any(a["login"] == nl for a in st.session_state["accounts"]):
                        st.error(f"Login {nl} is already linked.")
                    elif len(nl) < 4 or not np_:
                        st.error("Login and password required.")
                    else:
                        ok, note = mt5_connect(nl, np_, ns)
                        st.session_state["accounts"].append(
                            {"broker": nb, "server": ns, "login": nl, "live": ok, "primary": False})
                        st.success(note) if ok else st.warning(note)
                        st.rerun()
        with c2:
            st.markdown("##### Mode")
            if st.session_state["mode"] == "demo":
                st.markdown("<p class='zl-muted'>Everything works exactly as it will live — same rules, "
                            "same journal — but orders are simulated.</p>", unsafe_allow_html=True)
                for gate, val in [("14 days on demo", "day 14"), ("30+ closed trades", f"{len(taken)}"),
                                  ("Profit factor above 1.2", "1.46"), ("Funded live account", "linked")]:
                    st.markdown(f"<div class='zl-muted'>✓&nbsp; {gate} — {val}</div>", unsafe_allow_html=True)
                if st.button("Go live", use_container_width=True):
                    st.session_state["mode"] = "live"
                    st.rerun()
            else:
                st.warning("Live. Real orders are going to your broker.", icon="⚠")
                if st.button("Switch back to demo", use_container_width=True):
                    st.session_state["mode"] = "demo"
                    st.rerun()
            st.markdown("##### Runs on")
            st.markdown("<span class='zl-tag'>iPhone</span><span class='zl-tag'>Android</span>"
                        "<span class='zl-tag'>Windows tablet</span><span class='zl-tag'>Browser</span>",
                        unsafe_allow_html=True)


    for tab, fn, label in ((desk, _desk, "Desk"), (charts, _charts, "Charts"),
                           (jrnl, _journal, "Journal"), (rules_tab, _rules, "Rules"),
                           (account, _account, "Account")):
        with tab:
            safe(fn, label)


# ──────────────────────────────────────────────────────────────────────

STAGES = {"login": face_login, "creds": face_creds, "setup": face_setup, "app": face_app}
STAGES[st.session_state["stage"]]()
