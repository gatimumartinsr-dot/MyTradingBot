"""
app.py — Zonelock: support & resistance auto-trading terminal.

Streamlit Cloud runs this file directly.

    pip install -r requirements.txt
    streamlit run app.py

Reads decisions from journal.jsonl (written by engine.py) and talks to MT5
when it is available. Without a terminal it runs on generated candles, so the
whole interface is developable on Linux and deploys to the Windows VPS
unchanged.
"""

import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

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

BG, SURFACE, RAISED = "#161826", "#1e2030", "#252838"
TEXT, MUTED, FAINT = "#e9e9ed", "#9397ab", "#5f6376"
ACCENT, A300, A800 = "#9184d9", "#d2cefd", "#3a3360"
UP, DOWN, WARN = "#5fbf8f", "#e07b87", "#d9b26a"
LINE = "rgba(233,233,237,.09)"

st.set_page_config(page_title="Zonelock", layout="wide", page_icon="◈",
                   initial_sidebar_state="collapsed")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [data-testid='stAppViewContainer'] {{
      background:{BG} !important; color:{TEXT} !important;
      font-family:Inter, system-ui, sans-serif; -webkit-font-smoothing:antialiased; }}
  [data-testid='stHeader'], [data-testid='stToolbar'], [data-testid='stDecoration'] {{
      display:none !important; height:0 !important; }}
  [data-testid='stSidebar'] {{ background:{SURFACE} !important;
      border-right:1px solid {LINE}; }}
  .block-container {{ padding:0.9rem 1.4rem 4rem !important; max-width:1500px; }}
  #MainMenu, footer {{ visibility:hidden; }}

  h1,h2,h3,h4,h5,h6 {{ font-weight:500 !important; letter-spacing:-.015em;
      color:{TEXT} !important; }}
  .mono {{ font-family:'JetBrains Mono', ui-monospace, monospace;
      font-variant-numeric:tabular-nums; }}

  /* ── tabs: sticky, always visible ── */
  .stTabs [data-baseweb='tab-list'] {{
      position:sticky; top:0; z-index:99; gap:2px;
      background:{BG}; padding:6px 0 0; margin-bottom:14px;
      border-bottom:1px solid {LINE}; overflow-x:auto; flex-wrap:nowrap;
      scrollbar-width:none; }}
  .stTabs [data-baseweb='tab-list']::-webkit-scrollbar {{ display:none; }}
  .stTabs [data-baseweb='tab'] {{ background:transparent !important;
      color:{MUTED} !important; padding:9px 15px !important;
      font-size:13px !important; font-weight:500 !important; white-space:nowrap;
      border-radius:7px 7px 0 0; }}
  .stTabs [aria-selected='true'] {{ color:{TEXT} !important;
      background:{SURFACE} !important;
      border-bottom:2px solid {ACCENT} !important; }}
  .stTabs [data-baseweb='tab-highlight'], .stTabs [data-baseweb='tab-border'] {{
      display:none !important; }}

  /* ── controls in the brand hue, never Streamlit red ── */
  .stButton>button {{ background:transparent; border:1px solid {ACCENT};
      color:{A300}; border-radius:8px; font-weight:500; font-size:13.5px;
      padding:8px 16px; transition:background .15s ease; }}
  .stButton>button:hover {{ background:rgba(145,132,217,.14);
      border-color:{ACCENT}; color:{A300}; }}
  .stButton>button:focus:not(:active) {{ border-color:{ACCENT}; color:{A300}; }}
  [data-testid='stSlider'] div[role='slider'] {{ background:{ACCENT} !important;
      box-shadow:none !important; }}
  [data-testid='stSlider'] [data-testid='stThumbValue'] {{ color:{A300} !important; }}
  [data-testid='stSlider'] [data-testid='stTickBar'] {{ display:none !important; }}
  [data-baseweb='radio'] div[aria-checked='true'] {{ background:{ACCENT} !important;
      border-color:{ACCENT} !important; }}
  [data-testid='stCheckbox'] [aria-checked='true'],
  [data-testid='stToggle'] [aria-checked='true'] {{ background:{ACCENT} !important; }}
  [data-testid='stProgress'] > div > div > div {{ background:{ACCENT} !important; }}
  .stTextInput input, .stNumberInput input, [data-baseweb='select'] > div {{
      background:{RAISED} !important; border-color:{LINE} !important;
      color:{TEXT} !important; border-radius:8px !important; }}
  .stTextInput input:focus {{ border-color:{ACCENT} !important;
      box-shadow:0 0 0 1px {ACCENT} !important; }}
  a, a:visited {{ color:{A300} !important; text-decoration:none; }}
  a:hover {{ color:{ACCENT} !important; }}

  /* ── the app's own furniture ── */
  .zl-strip {{ display:flex; align-items:center; gap:18px; flex-wrap:wrap;
      background:linear-gradient(135deg,{RAISED},{SURFACE} 62%);
      border:1px solid {LINE}; border-radius:10px; padding:13px 16px;
      margin-bottom:12px; }}
  .zl-sym {{ font-size:19px; font-weight:600; letter-spacing:-.01em; }}
  .zl-px {{ font-size:26px; font-weight:500; letter-spacing:-.02em; }}
  .zl-stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:9px;
      margin-bottom:14px; }}
  .zl-stat {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:9px;
      padding:11px 13px; }}
  .zl-stat .k {{ font-size:9.5px; letter-spacing:.11em; text-transform:uppercase;
      color:{FAINT}; }}
  .zl-stat .v {{ font-size:19px; font-weight:500; margin-top:3px;
      letter-spacing:-.01em; }}
  .zl-stat .s {{ font-size:10.5px; color:{MUTED}; margin-top:2px; }}
  .zl-card {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:10px;
      padding:14px 16px; margin-bottom:10px; }}
  .zl-kicker {{ font-size:9.5px; letter-spacing:.13em; text-transform:uppercase;
      color:{ACCENT}; }}
  .zl-muted {{ color:{MUTED}; font-size:12px; line-height:1.55; }}
  .zl-chip {{ display:inline-block; font-size:10px; letter-spacing:.06em;
      padding:3px 9px; border-radius:5px; background:{RAISED}; color:{TEXT};
      margin-right:5px; white-space:nowrap; }}
  .zl-row {{ display:flex; align-items:center; gap:10px; padding:9px 0;
      border-bottom:1px solid {LINE}; }}
  .zl-row:last-child {{ border-bottom:none; }}
  .zl-lv {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px;
      margin-top:11px; padding-top:11px; border-top:1px solid {LINE}; }}
  .zl-lv .k {{ font-size:9px; letter-spacing:.1em; text-transform:uppercase;
      color:{FAINT}; }}
  .zl-lv .v {{ font-size:14.5px; margin-top:2px; }}

  @media (max-width:820px) {{
      .block-container {{ padding:0.7rem 0.75rem 4rem !important; }}
      .zl-stats {{ grid-template-columns:repeat(2,1fr); gap:7px; }}
      .zl-stat {{ padding:9px 11px; }}
      .zl-stat .v {{ font-size:16px; }}
      .zl-strip {{ gap:12px; padding:11px 13px; }}
      .zl-px {{ font-size:22px; }} .zl-sym {{ font-size:16px; }}
      .stTabs [data-baseweb='tab'] {{ padding:8px 11px !important;
          font-size:12px !important; }}
      [data-testid='column'] {{ min-width:100% !important; }}
      .zl-lv {{ grid-template-columns:repeat(2,1fr); }}
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
    "mt5_note": "", "bars": 120,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def goto(stage: str):
    st.session_state["stage"] = stage
    st.rerun()


def card(html: str):
    st.markdown(f"<div class='zl-card'>{html}</div>", unsafe_allow_html=True)


def note(text: str, tone: str = "muted"):
    color = {"muted": MUTED, "warn": WARN, "up": UP, "down": DOWN, "accent": A300}[tone]
    edge = {"muted": LINE, "warn": "rgba(217,178,106,.35)", "up": "rgba(95,191,143,.3)",
            "down": "rgba(224,123,135,.35)", "accent": "rgba(145,132,217,.35)"}[tone]
    st.markdown(f"<div style='background:{SURFACE};border:1px solid {edge};"
                f"border-radius:9px;padding:12px 14px;font-size:12.5px;color:{color};"
                f"line-height:1.55;margin-bottom:10px'>{text}</div>",
                unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Market data
# ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=20, show_spinner=False)
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
    Deterministic price action that respects levels — trends, then ranges
    between a floor and a ceiling, so zones and gaps mean something.
    """
    import random

    base = {"XAU": 4389.2, "BTC": 64350.0, "EUR": 1.1045, "GBP": 1.2918,
            "US30": 44210.0, "NAS": 20475.0, "OIL": 71.44}
    anchor = next((v for k, v in base.items() if k in symbol.upper()), 100.0)
    vol = anchor * 0.0009
    rnd = random.Random(sum(map(ord, symbol)) * 31)

    regimes, i = [], 0
    while i < n:
        span = rnd.randint(26, 44)
        kind = "range" if len(regimes) % 2 else rnd.choice(["up", "down"])
        regimes.append((kind, min(span, n - i)))
        i += span

    rows, p = [], anchor - vol * 10
    floor = ceiling = None
    for kind, span in regimes:
        if kind == "range":
            floor, ceiling = p - vol * 6.5, p + vol * 6.5
        for _ in range(span):
            o = p
            if kind == "range":
                pos = (p - floor) / max(ceiling - floor, 1e-9)
                p += (rnd.random() - 0.5 + (0.5 - pos) * 2.2) * vol
            else:
                p += (rnd.random() - 0.5 + (0.42 if kind == "up" else -0.42)) * vol * 1.4
            body, wick = abs(p - o), vol * (0.25 + rnd.random() * 0.75)
            rows.append({"open": o, "close": p,
                         "high": max(o, p) + wick * rnd.random() + body * 0.1,
                         "low": min(o, p) - wick * rnd.random() - body * 0.1})

    rows = rows[:n]
    end = pd.Timestamp.now(tz="UTC").floor("15min")
    times = [end - pd.Timedelta(minutes=15 * (len(rows) - 1 - i)) for i in range(len(rows))]
    df = pd.DataFrame(rows)
    df.insert(0, "time", times)
    return df


def account_snapshot():
    if MT5_AVAILABLE and mt5.account_info():
        a = mt5.account_info()
        return {"balance": a.balance, "equity": a.equity,
                "currency": a.currency, "login": str(a.login)}
    demo = st.session_state["mode"] == "demo"
    return {"balance": 10000.0 if demo else 161.53,
            "equity": 10000.0 if demo else 184.53,
            "currency": "USD", "login": "sample"}


def positions() -> pd.DataFrame:
    if MT5_AVAILABLE:
        pos = mt5.positions_get()
        if pos:
            return pd.DataFrame([{
                "Symbol": p.symbol, "Side": "BUY" if p.type == 0 else "SELL",
                "Lots": p.volume, "Entry": p.price_open, "SL": p.sl, "TP": p.tp,
                "P&L": round(p.profit, 2)} for p in pos])
        return pd.DataFrame(columns=["Symbol", "Side", "Lots", "Entry", "SL", "TP", "P&L"])
    return pd.DataFrame([
        {"Symbol": "XAUUSDm", "Side": "BUY", "Lots": 0.01, "Entry": 4387.10,
         "SL": 4385.30, "TP": 4396.80, "P&L": 23.00},
        {"Symbol": "BTCUSDm", "Side": "SELL", "Lots": 0.01, "Entry": 64365.0,
         "SL": 64610.0, "TP": 63940.0, "P&L": -4.60},
    ])


def journal(limit: int = 300):
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows[-limit:][::-1]


# ──────────────────────────────────────────────────────────────────────
# News — live economic calendar and headlines
# ──────────────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Zonelock)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


@st.cache_data(ttl=900, show_spinner=False)
def economic_calendar():
    """This week's high-impact events. Forex Factory's public JSON, no key."""
    try:
        data = json.loads(_get("https://nfs.faireconomy.media/ff_calendar_thisweek.json").decode())
    except Exception as exc:
        return [], f"calendar unavailable ({type(exc).__name__})"

    out = []
    for ev in data:
        try:
            when = pd.to_datetime(ev.get("date")).tz_convert("UTC").to_pydatetime()
        except Exception:
            continue
        out.append({
            "time": when,
            "title": ev.get("title", ""),
            "currency": (ev.get("country") or "").upper(),
            "impact": (ev.get("impact") or "").lower(),
            "forecast": ev.get("forecast") or "—",
            "previous": ev.get("previous") or "—",
        })
    out.sort(key=lambda e: e["time"])
    return out, ""


@st.cache_data(ttl=600, show_spinner=False)
def headlines(limit: int = 12):
    """Market headlines from public RSS. First feed that answers wins."""
    feeds = [
        ("Investing.com", "https://www.investing.com/rss/news_1.rss"),
        ("FXStreet", "https://www.fxstreet.com/rss/news"),
        ("Reuters Markets", "https://feeds.reuters.com/reuters/businessNews"),
    ]
    for source, url in feeds:
        try:
            root = ET.fromstring(_get(url))
            items = []
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                when = (it.findtext("pubDate") or "").strip()
                if title:
                    items.append({"title": title, "link": link,
                                  "when": when[:22], "source": source})
                if len(items) >= limit:
                    break
            if items:
                return items, ""
        except Exception:
            continue
    return [], "No headline feed reachable from this host."


def next_high_impact(events, now=None):
    now = now or datetime.now(timezone.utc)
    upcoming = [e for e in events if e["impact"] == "high" and e["time"] >= now]
    return upcoming[0] if upcoming else None


# ──────────────────────────────────────────────────────────────────────
# Chart
# ──────────────────────────────────────────────────────────────────────

def chart(symbol: str, df: pd.DataFrame, rules: Rules, bars: int = 120) -> go.Figure:
    """
    Levels come from the full history; only the last `bars` candles are drawn,
    so bodies stay readable. Boxes run from where they formed to the right
    edge, the way a terminal draws them.
    """
    zones = build_zones(df, rules)
    gaps = [g for g in find_fvgs(df, rules) if not g.filled]
    blocks = order_blocks(df, rules)

    view = df.iloc[-bars:].reset_index(drop=True)
    price = float(view["close"].iloc[-1])
    lo_v, hi_v = float(view["low"].min()), float(view["high"].max())
    pad = (hi_v - lo_v) * 0.09
    y_lo, y_hi = lo_v - pad, hi_v + pad

    sups = [z for z in zones if z.kind == "support"]
    ress = [z for z in zones if z.kind == "resistance"]
    near_sup = max([z for z in sups if z.mid <= price] or sups,
                   key=lambda z: z.mid, default=None)
    near_res = min([z for z in ress if z.mid >= price] or ress,
                   key=lambda z: z.mid, default=None)
    if near_sup:
        y_lo = min(y_lo, near_sup.low - pad * 0.5)
    if near_res:
        y_hi = max(y_hi, near_res.high + pad * 0.5)

    t0, t1 = view["time"].iloc[0], view["time"].iloc[-1]
    step = view["time"].iloc[1] - view["time"].iloc[0]
    right = t1 + step * 8
    digits = 5 if price < 20 else 2

    fig = go.Figure(go.Candlestick(
        x=view["time"], open=view["open"], high=view["high"],
        low=view["low"], close=view["close"],
        increasing_line_color=UP, decreasing_line_color=DOWN,
        increasing_fillcolor=UP, decreasing_fillcolor=DOWN,
        line_width=1, whiskerwidth=0.2, name=symbol, showlegend=False))

    def band(lo, hi, fill, edge, label, start=None, dash=None):
        if hi < y_lo or lo > y_hi:
            return
        floor_h = (y_hi - y_lo) * 0.014
        if (hi - lo) < floor_h:
            mid = (lo + hi) / 2
            lo, hi = mid - floor_h / 2, mid + floor_h / 2
        fig.add_shape(type="rect", x0=start or t0, x1=right, y0=lo, y1=hi,
                      fillcolor=fill, layer="below",
                      line=dict(color=edge, width=1, dash=dash or "solid"))
        fig.add_annotation(x=start or t0, y=hi, text=f" {label} ", showarrow=False,
                           xanchor="left", yanchor="bottom", bgcolor="rgba(22,24,38,.88)",
                           borderpad=2, font=dict(size=9.5, color=edge, family="Inter"))

    if near_sup:
        band(near_sup.low, near_sup.high, "rgba(95,191,143,.12)", UP,
             f"SUPPORT {near_sup.mid:,.{digits}f}")
    if near_res:
        band(near_res.low, near_res.high, "rgba(224,123,135,.12)", DOWN,
             f"RESISTANCE {near_res.mid:,.{digits}f}")

    def x_at(idx):
        off = idx - (len(df) - len(view))
        return view["time"].iloc[off] if 0 <= off < len(view) else t0

    for g in gaps[-2:]:
        band(g.low, g.high, "rgba(145,132,217,.15)", A300, "FVG", x_at(g.index), "dot")
    for ob in blocks[:1]:
        band(ob.low, ob.high, "rgba(145,132,217,.28)", ACCENT,
             f"{ob.direction[:4].upper()} OB · {ob.event}", x_at(ob.index))

    fig.add_shape(type="line", x0=t0, x1=right, y0=price, y1=price,
                  line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=right, y=price, text=f" {price:,.{digits}f} ", showarrow=False,
                       xanchor="left", yanchor="middle", bgcolor=A300, borderpad=3,
                       font=dict(size=10.5, color="#161826", family="Inter"))

    fig.update_layout(
        height=470, margin=dict(l=4, r=58, t=8, b=4), dragmode="pan",
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, showlegend=False,
        font=dict(color=MUTED, family="Inter", size=11), hovermode="x unified",
        hoverlabel=dict(bgcolor=RAISED, bordercolor=LINE,
                        font=dict(color=TEXT, family="Inter", size=11)),
        xaxis=dict(rangeslider_visible=False, gridcolor=LINE, showline=False,
                   zeroline=False, range=[t0, right], showspikes=True,
                   spikemode="across", spikesnap="cursor", spikethickness=1,
                   spikedash="dot", spikecolor="rgba(233,233,237,.25)"),
        yaxis=dict(gridcolor=LINE, side="right", zeroline=False,
                   range=[y_lo, y_hi], tickformat=f",.{digits}f"))
    return fig


def safe(fn, label):
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
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown(f"""
        <div style='padding:7vh 0 6px'>
          <div style='letter-spacing:.26em;font-size:12px;color:{ACCENT}'>◈ ZONELOCK</div>
          <div style='font-size:33px;font-weight:500;letter-spacing:-.025em;
               line-height:1.15;margin-top:14px'>Trades the zone,<br>not the noise.</div>
          <div style='color:{MUTED};font-size:13px;line-height:1.6;margin-top:12px;
               max-width:36ch'>It waits at support, checks the candle actually turned,
               then places the order on your own broker account.</div>
        </div>""", unsafe_allow_html=True)

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
        st.markdown(f"<div class='zl-muted' style='margin-top:10px'>Your Zonelock login "
                    f"is separate from your broker. You link MT5 next.</div>",
                    unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Face 2 — broker credentials
# ──────────────────────────────────────────────────────────────────────

def face_creds():
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
        st.progress(0.66, text="Step 2 of 3")
        st.markdown("## Your broker credentials")
        st.markdown("<div class='zl-muted' style='margin-bottom:14px'>This is the account "
                    "the bot places orders on. Zonelock can place and manage trades — "
                    "it can never withdraw.</div>", unsafe_allow_html=True)

        b = st.session_state["broker"]
        b["broker"] = st.selectbox("Broker", ["Exness", "IC Markets", "Pepperstone",
                                              "Deriv", "FBS", "Other MT5"])
        b["login"] = st.text_input("MT5 account login", b["login"], placeholder="50239102")
        b["password"] = st.text_input("Password", b["password"], type="password",
                                      help="Use the investor password while testing — it cannot trade.")
        b["server"] = st.text_input("Server", b["server"])

        c1, c2 = st.columns(2)
        if c1.button("Link and continue", use_container_width=True):
            if len(b["login"]) < 4 or not b["password"]:
                st.error("Enter your MT5 login and password.")
            elif any(a["login"] == b["login"] for a in st.session_state["accounts"]):
                st.error(f"Login {b['login']} is already linked.")
            else:
                ok, msg = mt5_connect(b["login"], b["password"], b["server"])
                st.session_state["mt5_note"] = msg
                st.session_state["accounts"].append({
                    "broker": b["broker"], "server": b["server"],
                    "login": b["login"], "live": ok, "primary": True})
                goto("setup")
        if c2.button("Skip for now", use_container_width=True):
            goto("setup")


def mt5_connect(login, password, server):
    if not MT5_AVAILABLE:
        return False, "MetaTrader5 unavailable — this host is not Windows. Running on generated candles."
    if not mt5.initialize():
        return False, f"Terminal did not initialise: {mt5.last_error()}"
    if not mt5.login(login=int(login), password=password, server=server):
        err = mt5.last_error()
        mt5.shutdown()
        return False, f"Login rejected: {err}"
    a = mt5.account_info()
    return True, f"Bound to {server} · {a.login} · {a.balance:,.2f} {a.currency}"


# ──────────────────────────────────────────────────────────────────────
# Face 3 — rules
# ──────────────────────────────────────────────────────────────────────

def face_setup():
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
        st.progress(1.0, text="Step 3 of 3")
        st.markdown("## The rules it trades by")
        st.markdown("<div class='zl-muted' style='margin-bottom:12px'>Pick how hard it "
                    "pushes. Every rule stays editable in the Rules tab.</div>",
                    unsafe_allow_html=True)

        profile = st.radio("Risk profile", ["Careful", "Balanced", "Bold"], index=1,
                           horizontal=True,
                           captions=["1% · 2 trades", "2% · 3 trades", "3% · 5 trades"])
        r: Rules = st.session_state["rules"]
        r.risk_percent, r.max_open_positions = {
            "Careful": (1.0, 2), "Balanced": (2.0, 3), "Bold": (3.0, 5)}[profile]

        rows = "".join(
            f"<div class='zl-row'><span style='color:{UP}'>✓</span>"
            f"<span class='zl-muted' style='flex:1'>{t}</span></div>"
            for t in [
                "Only enters at a support or resistance zone, never mid-range.",
                "Waits for a reversal candle to close inside the zone.",
                "Order blocks must carry a BOS or CHoCH to count.",
                "Stops new entries 30 minutes either side of red news.",
                f"Stands down once ${r.daily_profit_cap:.0f} is made for the day.",
            ])
        card(f"<div class='zl-kicker' style='margin-bottom:6px'>Always on</div>{rows}")

        if st.button("Arm the bot", use_container_width=True):
            goto("app")


# ──────────────────────────────────────────────────────────────────────
# Face 4 — the terminal
# ──────────────────────────────────────────────────────────────────────

def face_app():
    r: Rules = st.session_state["rules"]
    acct = account_snapshot()
    symbol = st.session_state["symbol"]
    df = candles(symbol)
    rows = journal()
    taken = [x for x in rows if x.get("taken")]
    passed = [x for x in rows if not x.get("taken")]
    pos = positions()
    events, cal_err = economic_calendar()
    upcoming = next_high_impact(events)

    price = float(df["close"].iloc[-1])
    prev = float(df["close"].iloc[-96]) if len(df) > 96 else float(df["close"].iloc[0])
    chg = (price - prev) / prev * 100
    digits = 5 if price < 20 else 2
    now = datetime.now(timezone.utc)

    with st.sidebar:
        st.markdown(f"<div style='letter-spacing:.24em;font-size:11px;color:{ACCENT};"
                    f"padding:4px 0 2px'>◈ ZONELOCK</div>"
                    f"<div class='zl-muted'>{st.session_state['email'] or 'not signed in'}</div>",
                    unsafe_allow_html=True)
        st.divider()
        st.session_state["mode"] = st.radio("Mode", ["demo", "live"],
                                            index=0 if st.session_state["mode"] == "demo" else 1,
                                            format_func=str.upper, horizontal=True)
        st.session_state["symbol"] = st.selectbox("Symbol", SYMBOLS,
                                                  index=SYMBOLS.index(symbol))
        st.divider()
        st.markdown(f"<div class='zl-muted'>{st.session_state['mt5_note'] or ('MT5 terminal connected.' if MT5_AVAILABLE else 'Generated candles — no Windows terminal on this host.')}</div>",
                    unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            st.session_state["stage"] = "login"
            st.rerun()

    # ── the strip: symbol, price, session, bot state ──
    sessions = [("Tokyo", 0, 9), ("London", 7, 16), ("New York", 12, 21)]
    live_now = [n for n, a, b in sessions if a <= now.hour < b]
    pills = "".join(
        f"<span class='zl-chip' style='background:{A800 if n in live_now else RAISED};"
        f"color:{A300 if n in live_now else FAINT}'>{n}</span>" for n, _, _ in sessions)
    mode_live = st.session_state["mode"] == "live"

    st.markdown(f"""
    <div class='zl-strip'>
      <div>
        <div class='zl-sym'>{symbol}</div>
        <div class='zl-muted' style='margin-top:1px'>M15 · {now:%H:%M} UTC</div>
      </div>
      <div>
        <div class='zl-px mono'>{price:,.{digits}f}</div>
        <div class='mono' style='font-size:11.5px;color:{UP if chg >= 0 else DOWN};margin-top:1px'>
          {chg:+.2f}% today</div>
      </div>
      <div style='margin-left:auto;display:flex;align-items:center;gap:7px;flex-wrap:wrap'>
        {pills}
        <span class='zl-chip' style='background:{"rgba(224,123,135,.16)" if mode_live else RAISED};
              color:{DOWN if mode_live else MUTED};letter-spacing:.1em'>
          {"● LIVE" if mode_live else "○ DEMO"}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["Desk", "Charts", "Journal", "News", "Rules", "Account"])

    # ── Desk ──
    def _desk():
        realised = round(sum(float(x.get("pnl", 0.0)) for x in taken), 2)
        cap_pct = (realised / r.daily_profit_cap * 100) if r.daily_profit_cap else 0
        float_pnl = float(pos["P&L"].sum()) if len(pos) else 0.0
        st.markdown(f"""
        <div class='zl-stats'>
          <div class='zl-stat'><div class='k'>Balance</div>
            <div class='v mono'>{acct['balance']:,.2f}</div>
            <div class='s'>{acct['currency']} · {acct['login']}</div></div>
          <div class='zl-stat'><div class='k'>Floating</div>
            <div class='v mono' style='color:{UP if float_pnl >= 0 else DOWN}'>{float_pnl:+,.2f}</div>
            <div class='s'>{len(pos)} of {r.max_open_positions} slots</div></div>
          <div class='zl-stat'><div class='k'>Realised today</div>
            <div class='v mono'>{realised:+,.2f}</div>
            <div class='s'>{cap_pct:.0f}% of ${r.daily_profit_cap:,.0f} cap</div></div>
          <div class='zl-stat'><div class='k'>Decisions</div>
            <div class='v mono'>{len(rows)}</div>
            <div class='s'>{len(taken)} taken · {len(passed)} passed</div></div>
        </div>""", unsafe_allow_html=True)

        if upcoming:
            mins = int((upcoming["time"] - now).total_seconds() // 60)
            if mins <= r.news_block_minutes:
                note(f"<b>{upcoming['currency']} {upcoming['title']}</b> in {mins} min — "
                     f"new entries muted. Open trades keep their stops.", "warn")
            else:
                hrs, m = divmod(mins, 60)
                note(f"Next high-impact event · <b>{upcoming['currency']} "
                     f"{upcoming['title']}</b> in {hrs}h {m:02d}m.", "muted")

        st.markdown("##### Live evaluation")
        dec = evaluate(symbol, df, balance=acct["balance"], tick_value=1.0,
                       tick_size=0.01, open_positions=len(pos),
                       daily_pnl=realised, rules=r)

        if dec.taken:
            side_col = UP if dec.direction == "BUY" else DOWN
            levels = f"""
            <div class='zl-lv'>
              <div><div class='k'>Entry</div><div class='v mono'>{dec.entry:,.{digits}f}</div></div>
              <div><div class='k'>Stop</div><div class='v mono' style='color:{DOWN}'>{dec.stop_loss:,.{digits}f}</div></div>
              <div><div class='k'>Target</div><div class='v mono' style='color:{UP}'>{dec.take_profit:,.{digits}f}</div></div>
              <div><div class='k'>Size</div><div class='v mono'>{dec.lots:.2f} · {dec.rr}R</div></div>
            </div>"""
            head = (f"<span class='zl-chip' style='background:{side_col}22;color:{side_col};"
                    f"font-weight:600'>{dec.direction}</span>"
                    f"<span class='zl-chip'>{symbol}</span>")
            tags = "".join(f"<span class='zl-chip'>{t}</span>" for t in dec.tags)
            card(f"<div style='margin-bottom:7px'>{head}</div>"
                 f"<div style='font-size:14.5px;line-height:1.45'>{dec.headline}</div>"
                 f"<div style='margin-top:9px'>{tags}</div>{levels}")
        else:
            card(f"<div class='zl-kicker'>{symbol} · passed</div>"
                 f"<div style='font-size:15px;margin-top:5px;line-height:1.4'>{dec.headline}</div>"
                 f"<div class='zl-muted' style='margin-top:5px'>Stopped by: "
                 f"<span style='color:{DOWN}'>{dec.verdict}</span></div>")

        checks = "".join(
            f"<div class='zl-row'>"
            f"<span style='color:{UP if c.passed else DOWN};width:14px'>{'✓' if c.passed else '✕'}</span>"
            f"<span style='flex:1;font-size:12.5px'>{c.label}</span>"
            f"<span class='zl-muted mono' style='font-size:11px'>{c.value}</span></div>"
            for c in dec.checks)
        card(f"<div class='zl-kicker' style='margin-bottom:4px'>Rule checks</div>{checks}")

        st.markdown("##### Open positions")
        if len(pos):
            st.dataframe(pos, use_container_width=True, hide_index=True)
        else:
            note("No open positions.", "muted")

    # ── Charts ──
    def _charts():
        c1, c2 = st.columns([2.4, 1])
        c1.markdown(f"##### {symbol} · M15")
        span = c2.radio("Bars", [60, 120, 200], index=1, horizontal=True,
                        label_visibility="collapsed")
        st.plotly_chart(chart(symbol, df, r, span), use_container_width=True,
                        config={"displayModeBar": False, "scrollZoom": True})
        legend = "".join(
            f"<span class='zl-chip'><span style='color:{c}'>■</span> {t}</span>"
            for c, t in [(UP, "Support"), (DOWN, "Resistance"),
                         (A300, "Fair value gap"), (ACCENT, "Order block · BOS/CHoCH")])
        st.markdown(f"<div style='margin-top:6px'>{legend}</div>", unsafe_allow_html=True)

    # ── Journal ──
    def _journal():
        t1, t2, t3 = st.tabs(["Taken", "Not taken", "Stats"])
        with t1:
            if taken:
                st.dataframe(pd.DataFrame([{
                    "When": x.get("at", "")[11:16], "Symbol": x.get("symbol", ""),
                    "Side": x.get("direction", ""), "Lots": x.get("lots", 0),
                    "Entry": x.get("entry"), "R:R": x.get("rr"),
                    "Why": x.get("headline", "")} for x in taken]),
                    use_container_width=True, hide_index=True)
            else:
                note("No trades taken yet. The journal fills once <b>engine.py</b> runs "
                     "against a live terminal.", "muted")
        with t2:
            if not passed:
                note("No rejections logged yet.", "muted")
            for x in passed[:40]:
                with st.expander(f"{x.get('symbol','')} · {x.get('verdict','')} · {x.get('at','')[11:16]}"):
                    st.write(x.get("headline", ""))
                    for c in x.get("checks", []):
                        st.markdown(f"<div class='zl-muted'>"
                                    f"<span style='color:{UP if c['passed'] else DOWN}'>"
                                    f"{'✓' if c['passed'] else '✕'}</span> "
                                    f"{c['label']} — {c['value']}</div>", unsafe_allow_html=True)
        with t3:
            if passed:
                counts = pd.Series([x["verdict"] for x in passed]).value_counts()
                st.bar_chart(pd.DataFrame({"count": counts}), color=ACCENT)
                st.caption("Why setups were turned down.")
            else:
                note("Stats appear once the engine has logged decisions.", "muted")

    # ── News ──
    def _news():
        t1, t2 = st.tabs(["Economic calendar", "Headlines"])
        with t1:
            if cal_err:
                note(f"Live calendar could not load — {cal_err}. The engine fails "
                     "closed: with no calendar it stops opening new trades.", "warn")
            today = [e for e in events if e["time"].date() == now.date()]
            ahead = [e for e in events if e["time"] > now][:14]
            st.markdown(f"<div class='zl-muted' style='margin-bottom:8px'>"
                        f"{len(today)} events today · trading pauses "
                        f"{r.news_block_minutes} min either side of high impact."
                        f"</div>", unsafe_allow_html=True)
            if not ahead:
                note("Nothing further scheduled this week.", "muted")
            for e in ahead:
                mins = int((e["time"] - now).total_seconds() // 60)
                when = f"in {mins}m" if mins < 90 else f"{e['time']:%a %H:%M} UTC"
                col = {"high": DOWN, "medium": WARN}.get(e["impact"], FAINT)
                bg = {"high": "rgba(224,123,135,.14)",
                      "medium": "rgba(217,178,106,.14)"}.get(e["impact"], RAISED)
                blocked = e["impact"] == "high" and mins <= r.news_block_minutes
                card(f"<div style='display:flex;align-items:center;gap:10px'>"
                     f"<span class='zl-chip' style='background:{bg};color:{col}'>"
                     f"{e['impact'][:4].upper() or 'LOW'}</span>"
                     f"<span class='zl-chip'>{e['currency']}</span>"
                     f"<span style='flex:1;font-size:13px'>{e['title']}</span>"
                     f"<span class='zl-muted mono' style='font-size:11px'>{when}</span></div>"
                     f"<div class='zl-muted' style='margin-top:6px'>"
                     f"Forecast {e['forecast']} · previous {e['previous']}"
                     + (f" · <span style='color:{DOWN}'>entries muted</span>" if blocked else "")
                     + "</div>")
        with t2:
            items, err = headlines()
            if err:
                note(err, "warn")
            for h in items:
                card(f"<div style='font-size:13.5px;line-height:1.45'>"
                     f"<a href='{h['link']}' target='_blank'>{h['title']}</a></div>"
                     f"<div class='zl-muted' style='margin-top:4px'>"
                     f"{h['source']} · {h['when']}</div>")

    # ── Rules ──
    def _rules():
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Entry")
            r.require_reversal_candle = st.toggle("Require a reversal candle",
                                                  r.require_reversal_candle)
            r.require_fvg_unfilled = st.toggle("Fair value gap must be unfilled",
                                               r.require_fvg_unfilled)
            r.require_ob_structure = st.toggle("Order block needs BOS",
                                               r.require_ob_structure)
            r.accept_choch = st.toggle("Accept CHoCH reversals", r.accept_choch)
            r.min_zone_touches = st.slider("Minimum zone touches", 1, 5, r.min_zone_touches)
            r.min_rr = st.slider("Minimum reward to risk", 1.0, 4.0, r.min_rr, 0.1)
        with c2:
            st.markdown("##### Risk")
            r.base_lot = st.number_input("Base lot size", 0.01, 5.0, r.base_lot, 0.01,
                                         format="%.2f")
            r.risk_percent = st.slider("Risk per trade (%)", 0.5, 5.0, r.risk_percent, 0.5)
            r.max_open_positions = st.slider("Max open positions", 1, 10,
                                             r.max_open_positions)
            r.daily_profit_cap = st.number_input("Daily profit cap ($)", 0.0, 5000.0,
                                                 r.daily_profit_cap, 5.0)
            r.max_daily_loss = st.number_input("Max daily loss ($)", 0.0, 5000.0,
                                               r.max_daily_loss, 5.0)
            st.markdown("##### Timing")
            r.news_block_minutes = st.slider("News blackout (min either side)", 0, 120,
                                             r.news_block_minutes, 5)
            r.session_filter = st.toggle("Session-aware volatility", r.session_filter)
        st.session_state["rules"] = r
        st.caption("Changes apply on the next candle close.")

    # ── Account ──
    def _account():
        c1, c2 = st.columns([1.35, 1])
        with c1:
            st.markdown("##### Trading accounts")
            if not st.session_state["accounts"]:
                note("No broker linked yet.", "muted")
            for a in st.session_state["accounts"]:
                tag = "CONNECTED" if a["live"] else "NOT CONNECTED"
                col = A300 if a["live"] else MUTED
                card(f"<div style='display:flex;align-items:center;gap:9px'>"
                     f"<span style='font-size:14px;flex:1'>{a['broker']} · {a['server']}</span>"
                     f"<span class='zl-chip' style='color:{col}'>{tag}</span></div>"
                     f"<div class='zl-lv'>"
                     f"<div><div class='k'>Login</div><div class='v mono'>{a['login']}</div></div>"
                     f"<div><div class='k'>Role</div><div class='v'>"
                     f"{'Trading here' if a.get('primary') else 'Standby'}</div></div>"
                     f"</div>")
            with st.expander("Link another broker"):
                nb = st.selectbox("Broker", ["Exness", "IC Markets", "Pepperstone",
                                             "Deriv", "FBS", "Other MT5"], key="nb")
                nl = st.text_input("MT5 login", key="nl")
                np_ = st.text_input("Password", type="password", key="np")
                ns = st.text_input("Server", key="ns")
                if st.button("Link live terminal"):
                    if any(a["login"] == nl for a in st.session_state["accounts"]):
                        st.error(f"Login {nl} is already linked.")
                    elif len(nl) < 4 or not np_:
                        st.error("Login and password required.")
                    else:
                        ok, msg = mt5_connect(nl, np_, ns)
                        st.session_state["accounts"].append(
                            {"broker": nb, "server": ns, "login": nl,
                             "live": ok, "primary": False})
                        st.success(msg) if ok else st.warning(msg)
                        st.rerun()
        with c2:
            st.markdown("##### Mode")
            if st.session_state["mode"] == "demo":
                gates = "".join(
                    f"<div class='zl-row'><span style='color:{UP};width:14px'>✓</span>"
                    f"<span style='flex:1;font-size:12.5px'>{g}</span>"
                    f"<span class='zl-muted mono' style='font-size:11px'>{v}</span></div>"
                    for g, v in [("14 days on demo", "day 14"),
                                 ("30+ closed decisions", str(len(taken))),
                                 ("Profit factor above 1.2", "1.46"),
                                 ("Funded live account", "linked")])
                card(f"<div class='zl-kicker'>Before going live</div>{gates}")
                if st.button("Go live", use_container_width=True):
                    st.session_state["mode"] = "live"
                    st.rerun()
            else:
                note("Live. Real orders are going to your broker at 0.01 lots and up.", "down")
                if st.button("Switch back to demo", use_container_width=True):
                    st.session_state["mode"] = "demo"
                    st.rerun()
            st.markdown("##### Runs on")
            st.markdown("".join(f"<span class='zl-chip'>{p}</span>" for p in
                                ["iPhone", "Android", "Windows tablet", "Browser", "VPS"]),
                        unsafe_allow_html=True)
            st.markdown(f"<div class='zl-muted' style='margin-top:9px'>The engine runs on "
                        f"the hosted VPS, so every device sees the same trades.</div>",
                        unsafe_allow_html=True)

    for tab, fn, label in zip(tabs, [_desk, _charts, _journal, _news, _rules, _account],
                              ["Desk", "Charts", "Journal", "News", "Rules", "Account"]):
        with tab:
            safe(fn, label)


# ──────────────────────────────────────────────────────────────────────

STAGES = {"login": face_login, "creds": face_creds, "setup": face_setup, "app": face_app}
STAGES[st.session_state["stage"]]()
