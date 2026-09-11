"""
app.py — Zonelock: support & resistance setup scanner.

Reads free market data, applies your rules, and hands you trade setups to
place yourself on MT5. No broker connection, no credentials, no Windows.

    pip install -r requirements.txt
    streamlit run app.py
"""

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market import SYMBOLS, DataError, fetch, pips
from strategy import (Rules, atr, build_zones, confluence, daily_zones,
                      evaluate, find_fvgs, grade, order_blocks)

PICKS = os.environ.get("ZONELOCK_PICKS", "picks.jsonl")

BG, SURFACE, RAISED = "#161826", "#1e2030", "#252838"
TEXT, MUTED, FAINT = "#e9e9ed", "#9397ab", "#5f6376"
ACCENT, A300, A800 = "#9184d9", "#d2cefd", "#3a3360"
UP, DOWN, WARN = "#5fbf8f", "#e07b87", "#d9b26a"
LINE = "rgba(233,233,237,.09)"
GRADE_COLOR = {"A": UP, "B": A300, "C": WARN, "—": FAINT}

st.set_page_config(page_title="Zonelock Scanner", layout="wide", page_icon="◈",
                   initial_sidebar_state="collapsed")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
  html, body, [data-testid='stAppViewContainer'] {{ background:{BG} !important;
      color:{TEXT} !important; font-family:Inter, system-ui, sans-serif;
      -webkit-font-smoothing:antialiased; }}
  [data-testid='stHeader'], [data-testid='stToolbar'], [data-testid='stDecoration'] {{
      display:none !important; height:0 !important; }}
  [data-testid='stSidebar'] {{ background:{SURFACE} !important; border-right:1px solid {LINE}; }}
  .block-container {{ padding:0.9rem 1.4rem 4rem !important; max-width:1500px; }}
  #MainMenu, footer {{ visibility:hidden; }}
  h1,h2,h3,h4,h5,h6 {{ font-weight:500 !important; letter-spacing:-.015em; color:{TEXT} !important; }}
  .mono {{ font-family:'JetBrains Mono', ui-monospace, monospace; font-variant-numeric:tabular-nums; }}

  .stTabs [data-baseweb='tab-list'] {{ position:sticky; top:0; z-index:99; gap:2px;
      background:{BG}; padding:6px 0 0; margin-bottom:14px; border-bottom:1px solid {LINE};
      overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none; }}
  .stTabs [data-baseweb='tab-list']::-webkit-scrollbar {{ display:none; }}
  .stTabs [data-baseweb='tab'] {{ background:transparent !important; color:{MUTED} !important;
      padding:9px 15px !important; font-size:13px !important; font-weight:500 !important;
      white-space:nowrap; border-radius:7px 7px 0 0; }}
  .stTabs [aria-selected='true'] {{ color:{TEXT} !important; background:{SURFACE} !important;
      border-bottom:2px solid {ACCENT} !important; }}
  .stTabs [data-baseweb='tab-highlight'], .stTabs [data-baseweb='tab-border'] {{ display:none !important; }}

  .stButton>button {{ background:transparent; border:1px solid {ACCENT}; color:{A300};
      border-radius:8px; font-weight:500; font-size:13.5px; padding:8px 16px; }}
  .stButton>button:hover {{ background:rgba(145,132,217,.14); border-color:{ACCENT}; color:{A300}; }}
  .stButton>button:focus:not(:active) {{ border-color:{ACCENT}; color:{A300}; }}
  [data-testid='stSlider'] div[role='slider'] {{ background:{ACCENT} !important; box-shadow:none !important; }}
  [data-testid='stSlider'] [data-testid='stThumbValue'] {{ color:{A300} !important; }}
  [data-testid='stSlider'] [data-testid='stTickBar'] {{ display:none !important; }}
  [data-baseweb='radio'] div[aria-checked='true'] {{ background:{ACCENT} !important; border-color:{ACCENT} !important; }}
  [data-testid='stCheckbox'] [aria-checked='true'], [data-testid='stToggle'] [aria-checked='true'] {{
      background:{ACCENT} !important; }}
  [data-testid='stProgress'] > div > div > div {{ background:{ACCENT} !important; }}
  .stTextInput input, .stNumberInput input, [data-baseweb='select'] > div {{
      background:{RAISED} !important; border-color:{LINE} !important; color:{TEXT} !important;
      border-radius:8px !important; }}
  .stTextInput input:focus {{ border-color:{ACCENT} !important; box-shadow:0 0 0 1px {ACCENT} !important; }}
  a, a:visited {{ color:{A300} !important; text-decoration:none; }}
  a:hover {{ color:{ACCENT} !important; }}
  code {{ background:{RAISED} !important; color:{A300} !important; }}

  .zl-strip {{ display:flex; align-items:center; gap:18px; flex-wrap:wrap;
      background:linear-gradient(135deg,{RAISED},{SURFACE} 62%); border:1px solid {LINE};
      border-radius:10px; padding:13px 16px; margin-bottom:12px; }}
  .zl-stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:9px; margin-bottom:14px; }}
  .zl-stat {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:9px; padding:11px 13px; }}
  .zl-stat .k {{ font-size:9.5px; letter-spacing:.11em; text-transform:uppercase; color:{FAINT}; }}
  .zl-stat .v {{ font-size:19px; font-weight:500; margin-top:3px; letter-spacing:-.01em; }}
  .zl-stat .s {{ font-size:10.5px; color:{MUTED}; margin-top:2px; }}
  .zl-card {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:10px;
      padding:14px 16px; margin-bottom:10px; }}
  .zl-kicker {{ font-size:9.5px; letter-spacing:.13em; text-transform:uppercase; color:{ACCENT}; }}
  .zl-muted {{ color:{MUTED}; font-size:12px; line-height:1.55; }}
  .zl-chip {{ display:inline-block; font-size:10px; letter-spacing:.06em; padding:3px 9px;
      border-radius:5px; background:{RAISED}; color:{TEXT}; margin-right:5px; white-space:nowrap; }}
  .zl-row {{ display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid {LINE}; }}
  .zl-row:last-child {{ border-bottom:none; }}
  .zl-lv {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:11px;
      padding-top:11px; border-top:1px solid {LINE}; }}
  .zl-lv .k {{ font-size:9px; letter-spacing:.1em; text-transform:uppercase; color:{FAINT}; }}
  .zl-lv .v {{ font-size:14.5px; margin-top:2px; }}
  .zl-grade {{ width:30px; height:30px; border-radius:8px; display:inline-flex;
      align-items:center; justify-content:center; font-size:14px; font-weight:600; flex:none; }}
  .zl-ticket {{ background:{RAISED}; border:1px dashed {ACCENT}; border-radius:9px;
      padding:13px 15px; font-family:'JetBrains Mono', monospace; font-size:12.5px;
      line-height:1.85; color:{TEXT}; }}

  @media (max-width:820px) {{
      .block-container {{ padding:0.7rem 0.75rem 4rem !important; }}
      .zl-stats {{ grid-template-columns:repeat(2,1fr); gap:7px; }}
      .zl-stat {{ padding:9px 11px; }} .zl-stat .v {{ font-size:16px; }}
      .zl-strip {{ gap:12px; padding:11px 13px; }}
      .stTabs [data-baseweb='tab'] {{ padding:8px 11px !important; font-size:12px !important; }}
      [data-testid='column'] {{ min-width:100% !important; }}
      .zl-lv {{ grid-template-columns:repeat(2,1fr); }}
  }}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────

DEFAULTS = {
    "stage": "login", "user": "", "email": "", "rules": Rules(),
    "symbol": "XAUUSD", "scan": None, "scanned_at": None,
    "tg_token": "", "tg_chat": "", "td_key": "",
    "account_size": 1000.0, "watch": list(SYMBOLS.keys()),
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def card(html: str):
    st.markdown(f"<div class='zl-card'>{html}</div>", unsafe_allow_html=True)


def note(text: str, tone: str = "muted"):
    color = {"muted": MUTED, "warn": WARN, "up": UP, "down": DOWN, "accent": A300}[tone]
    edge = {"muted": LINE, "warn": "rgba(217,178,106,.35)", "up": "rgba(95,191,143,.3)",
            "down": "rgba(224,123,135,.35)", "accent": "rgba(145,132,217,.35)"}[tone]
    st.markdown(f"<div style='background:{SURFACE};border:1px solid {edge};border-radius:9px;"
                f"padding:12px 14px;font-size:12.5px;color:{color};line-height:1.55;"
                f"margin-bottom:10px'>{text}</div>", unsafe_allow_html=True)


def _get(url: str, timeout: int = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Zonelock)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ── news ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=900, show_spinner=False)
def economic_calendar():
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
        out.append({"time": when, "title": ev.get("title", ""),
                    "currency": (ev.get("country") or "").upper(),
                    "impact": (ev.get("impact") or "").lower(),
                    "forecast": ev.get("forecast") or "—",
                    "previous": ev.get("previous") or "—"})
    out.sort(key=lambda e: e["time"])
    return out, ""


@st.cache_data(ttl=600, show_spinner=False)
def headlines(limit: int = 12):
    for source, url in [("Investing.com", "https://www.investing.com/rss/news_1.rss"),
                        ("FXStreet", "https://www.fxstreet.com/rss/news"),
                        ("Reuters", "https://feeds.reuters.com/reuters/businessNews")]:
        try:
            root = ET.fromstring(_get(url))
            items = []
            for it in root.iter("item"):
                t = (it.findtext("title") or "").strip()
                if t:
                    items.append({"title": t, "link": (it.findtext("link") or "").strip(),
                                  "when": (it.findtext("pubDate") or "")[:22], "source": source})
                if len(items) >= limit:
                    break
            if items:
                return items, ""
        except Exception:
            continue
    return [], "No headline feed reachable."


def next_high_impact(events, now=None):
    now = now or datetime.now(timezone.utc)
    up = [e for e in events if e["impact"] == "high" and e["time"] >= now]
    return up[0] if up else None


# ── alerts ───────────────────────────────────────────────────────────

def telegram(text: str) -> tuple[bool, str]:
    tok, chat = st.session_state["tg_token"], st.session_state["tg_chat"]
    if not (tok and chat):
        return False, "Telegram not configured."
    try:
        url = (f"https://api.telegram.org/bot{tok}/sendMessage?chat_id={chat}"
               f"&parse_mode=HTML&text={urllib.parse.quote(text)}")
        ok = json.loads(_get(url).decode()).get("ok", False)
        return ok, "Sent." if ok else "Telegram rejected the message."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


# ── the scan ─────────────────────────────────────────────────────────

@st.cache_data(ttl=180, show_spinner=False)
def candles(symbol: str, interval: str, limit: int, td_key: str):
    return fetch(symbol, interval, limit, td_key)


def analyse(symbol: str, rules: Rules, td_key: str) -> dict:
    m15 = candles(symbol, "15m", 400, td_key)
    try:
        d1 = candles(symbol, "1d", 120, td_key)
    except Exception:
        d1 = None

    price = float(m15["close"].iloc[-1])
    a = atr(m15, 14)
    levels = daily_zones(d1, price) if d1 is not None else []

    dec = evaluate(symbol, m15, balance=st.session_state["account_size"],
                   tick_value=1.0, tick_size=SYMBOLS[symbol]["pip"], rules=rules)
    conf = confluence(dec, levels, a) if dec.taken else []

    return {"symbol": symbol, "decision": dec, "price": price, "atr": a,
            "levels": levels, "confluence": conf, "grade": grade(dec, conf),
            "m15": m15, "d1": d1}


def run_scan(rules: Rules):
    out, failed = [], []
    watch = st.session_state["watch"]
    bar = st.progress(0.0, text="Scanning…")
    for i, sym in enumerate(watch, 1):
        bar.progress(i / len(watch), text=f"Scanning {sym}…")
        try:
            out.append(analyse(sym, rules, st.session_state["td_key"]))
        except (DataError, Exception) as exc:
            failed.append(f"{sym}: {exc}")
    bar.empty()
    order = {"A": 0, "B": 1, "C": 2, "—": 3}
    out.sort(key=lambda r: (order[r["grade"]], -(r["decision"].rr or 0)))
    st.session_state["scan"] = {"rows": out, "failed": failed}
    st.session_state["scanned_at"] = datetime.now(timezone.utc)


def log_pick(row: dict):
    d = row["decision"]
    entry = {"at": datetime.now(timezone.utc).isoformat(), "symbol": row["symbol"],
             "mt5": SYMBOLS[row["symbol"]]["mt5"], "grade": row["grade"],
             "direction": d.direction, "entry": d.entry, "sl": d.stop_loss,
             "tp": d.take_profit, "rr": d.rr, "lots": d.lots,
             "headline": d.headline, "tags": d.tags,
             "confluence": row["confluence"], "outcome": "pending"}
    with open(PICKS, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def picks(limit: int = 200):
    if not os.path.exists(PICKS):
        return []
    with open(PICKS, encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return rows[-limit:][::-1]


# ── chart ────────────────────────────────────────────────────────────

def chart(row: dict, rules: Rules, bars: int = 120, show_daily: bool = True) -> go.Figure:
    symbol, df = row["symbol"], row["m15"]
    digits = SYMBOLS[symbol]["digits"]
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
    near_sup = max([z for z in sups if z.mid <= price] or sups, key=lambda z: z.mid, default=None)
    near_res = min([z for z in ress if z.mid >= price] or ress, key=lambda z: z.mid, default=None)
    if near_sup:
        y_lo = min(y_lo, near_sup.low - pad * 0.5)
    if near_res:
        y_hi = max(y_hi, near_res.high + pad * 0.5)

    t0, t1 = view["time"].iloc[0], view["time"].iloc[-1]
    step = view["time"].iloc[1] - view["time"].iloc[0]
    right = t1 + step * 9

    fig = go.Figure(go.Candlestick(
        x=view["time"], open=view["open"], high=view["high"], low=view["low"],
        close=view["close"], increasing_line_color=UP, decreasing_line_color=DOWN,
        increasing_fillcolor=UP, decreasing_fillcolor=DOWN, line_width=1,
        whiskerwidth=0.2, name=symbol, showlegend=False))

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

    if show_daily:
        for lv in row["levels"][:5]:
            if not (y_lo < lv.price < y_hi):
                continue
            col = {"resistance": DOWN, "support": UP}.get(lv.kind, FAINT)
            fig.add_shape(type="line", x0=t0, x1=right, y0=lv.price, y1=lv.price,
                          line=dict(color=col, width=1, dash="dash"))
            fig.add_annotation(x=t1, y=lv.price, text=f" {lv.name} ", showarrow=False,
                               xanchor="right", yanchor="bottom", bgcolor="rgba(22,24,38,.85)",
                               borderpad=2, font=dict(size=9, color=col, family="Inter"))

    d = row["decision"]
    if d.taken:
        for level, col, tag in [(d.entry, A300, "ENTRY"), (d.stop_loss, DOWN, "SL"),
                                (d.take_profit, UP, "TP")]:
            fig.add_shape(type="line", x0=t1 - step * 25, x1=right, y0=level, y1=level,
                          line=dict(color=col, width=1.4))
            fig.add_annotation(x=right, y=level, text=f" {tag} {level:,.{digits}f} ",
                               showarrow=False, xanchor="left", yanchor="middle",
                               bgcolor=col, borderpad=2,
                               font=dict(size=9.5, color="#161826", family="Inter"))
    else:
        fig.add_shape(type="line", x0=t0, x1=right, y0=price, y1=price,
                      line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=right, y=price, text=f" {price:,.{digits}f} ", showarrow=False,
                           xanchor="left", yanchor="middle", bgcolor=A300, borderpad=3,
                           font=dict(size=10.5, color="#161826", family="Inter"))

    fig.update_layout(
        height=470, margin=dict(l=4, r=88, t=8, b=4), dragmode="pan",
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, showlegend=False,
        font=dict(color=MUTED, family="Inter", size=11), hovermode="x unified",
        hoverlabel=dict(bgcolor=RAISED, bordercolor=LINE,
                        font=dict(color=TEXT, family="Inter", size=11)),
        xaxis=dict(rangeslider_visible=False, gridcolor=LINE, showline=False, zeroline=False,
                   range=[t0, right], showspikes=True, spikemode="across", spikesnap="cursor",
                   spikethickness=1, spikedash="dot", spikecolor="rgba(233,233,237,.25)"),
        yaxis=dict(gridcolor=LINE, side="right", zeroline=False, range=[y_lo, y_hi],
                   tickformat=f",.{digits}f"))
    return fig


def safe(fn, label):
    try:
        fn()
    except Exception as exc:
        st.error(f"{label} could not render: {type(exc).__name__} — {exc}")
        with st.expander("Details"):
            import traceback
            st.code(traceback.format_exc())


# ── login ────────────────────────────────────────────────────────────

def face_login():
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown(f"""
        <div style='padding:8vh 0 6px'>
          <div style='letter-spacing:.26em;font-size:12px;color:{ACCENT}'>◈ ZONELOCK</div>
          <div style='font-size:33px;font-weight:500;letter-spacing:-.025em;line-height:1.15;
               margin-top:14px'>Finds the zone.<br>You place the trade.</div>
          <div style='color:{MUTED};font-size:13px;line-height:1.6;margin-top:12px;max-width:38ch'>
            Scans gold, FX, indices, crypto and oil for reversals at support and resistance,
            marks the fair value gaps and order blocks, and hands you the exact order to
            place on MT5.</div>
        </div>""", unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign in", "Create account"])
        with tab_in:
            email = st.text_input("Email", "martins@zonelock.app", key="li_email")
            pwd = st.text_input("Password", "helix2026", type="password", key="li_pass")
            if st.button("Sign in", use_container_width=True):
                if email and pwd:
                    st.session_state.update(email=email, user=email.split("@")[0].title(),
                                            stage="app")
                    st.rerun()
                else:
                    st.error("Enter your email and password.")
        with tab_up:
            name = st.text_input("Full name", key="su_name")
            em2 = st.text_input("Email", key="su_email")
            pw2 = st.text_input("Password", type="password", key="su_pass")
            if st.button("Create account", use_container_width=True):
                if name and em2 and len(pw2) >= 6:
                    st.session_state.update(user=name, email=em2, stage="app")
                    st.rerun()
                else:
                    st.error("Name, email and a password of 6+ characters.")

        st.markdown(f"<div class='zl-muted' style='margin-top:12px'>No broker login needed — "
                    f"Zonelock never touches your account.</div>", unsafe_allow_html=True)


# ── the scanner ──────────────────────────────────────────────────────

def face_app():
    r: Rules = st.session_state["rules"]
    now = datetime.now(timezone.utc)
    events, cal_err = economic_calendar()
    upcoming = next_high_impact(events, now)

    with st.sidebar:
        st.markdown(f"<div style='letter-spacing:.24em;font-size:11px;color:{ACCENT};"
                    f"padding:4px 0 2px'>◈ ZONELOCK</div>"
                    f"<div class='zl-muted'>{st.session_state['email']}</div>",
                    unsafe_allow_html=True)
        st.divider()
        st.session_state["watch"] = st.multiselect(
            "Watchlist", list(SYMBOLS.keys()), st.session_state["watch"])
        st.session_state["account_size"] = st.number_input(
            "Account size ($)", 50.0, 1_000_000.0, st.session_state["account_size"], 50.0,
            help="Used to size the lots the setup card suggests.")
        st.divider()
        st.markdown("<div class='zl-muted'>Free market data · Yahoo Finance. "
                    "No broker connection.</div>", unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            st.session_state["stage"] = "login"
            st.rerun()

    sessions = [("Tokyo", 0, 9), ("London", 7, 16), ("New York", 12, 21)]
    live_now = [n for n, a, b in sessions if a <= now.hour < b]
    pill_html = "".join(
        f"<span class='zl-chip' style='background:{A800 if n in live_now else RAISED};"
        f"color:{A300 if n in live_now else FAINT}'>{n}</span>" for n, _, _ in sessions)
    scanned = st.session_state["scanned_at"]
    age = f"{int((now - scanned).total_seconds() // 60)}m ago" if scanned else "not yet"

    st.markdown(f"""
    <div class='zl-strip'>
      <div><div style='font-size:19px;font-weight:600'>Setup scanner</div>
        <div class='zl-muted' style='margin-top:1px'>{len(st.session_state['watch'])} symbols ·
        M15 · last scan {age}</div></div>
      <div style='margin-left:auto;display:flex;align-items:center;gap:7px;flex-wrap:wrap'>
        {pill_html}<span class='zl-chip'>{now:%H:%M} UTC</span></div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["Scanner", "Setup", "Chart", "Daily zones", "Picks", "News", "Rules", "Alerts"])
    scan = st.session_state["scan"]

    # ── Scanner ──
    def _scanner():
        c1, c2 = st.columns([1, 3])
        if c1.button("Scan now", use_container_width=True):
            run_scan(r)
            st.rerun()

        if upcoming:
            mins = int((upcoming["time"] - now).total_seconds() // 60)
            if mins <= r.news_block_minutes:
                note(f"<b>{upcoming['currency']} {upcoming['title']}</b> in {mins} min — "
                     f"setups on {upcoming['currency']} pairs are marked as news-blocked.", "warn")
            else:
                h, m = divmod(mins, 60)
                note(f"Next high-impact event · <b>{upcoming['currency']} "
                     f"{upcoming['title']}</b> in {h}h {m:02d}m.", "muted")

        if not scan:
            note("Press <b>Scan now</b> to analyse your watchlist. Each symbol is checked "
                 "against every rule and graded A, B or C.", "accent")
            return

        rows = scan["rows"]
        found = [x for x in rows if x["decision"].taken]
        a_grade = [x for x in found if x["grade"] == "A"]
        st.markdown(f"""
        <div class='zl-stats'>
          <div class='zl-stat'><div class='k'>Scanned</div><div class='v mono'>{len(rows)}</div>
            <div class='s'>symbols on M15</div></div>
          <div class='zl-stat'><div class='k'>Setups found</div>
            <div class='v mono' style='color:{UP if found else MUTED}'>{len(found)}</div>
            <div class='s'>{len(rows)-len(found)} passed the rules</div></div>
          <div class='zl-stat'><div class='k'>A-grade</div>
            <div class='v mono' style='color:{UP if a_grade else MUTED}'>{len(a_grade)}</div>
            <div class='s'>best confluence</div></div>
          <div class='zl-stat'><div class='k'>Data</div><div class='v mono'>Free</div>
            <div class='s'>Yahoo Finance</div></div>
        </div>""", unsafe_allow_html=True)

        if scan["failed"]:
            with st.expander(f"{len(scan['failed'])} symbols could not be fetched"):
                for f in scan["failed"]:
                    st.markdown(f"<div class='zl-muted'>{f}</div>", unsafe_allow_html=True)

        st.markdown("##### Setups")
        if not found:
            note("Nothing qualifies right now. That is the system working — it only calls "
                 "a setup when price is at a zone <i>and</i> a candle has confirmed it.", "muted")

        for row in found:
            d, sym = row["decision"], row["symbol"]
            dig = SYMBOLS[sym]["digits"]
            g, gc = row["grade"], GRADE_COLOR[row["grade"]]
            side = UP if d.direction == "BUY" else DOWN
            conf = (" · ".join(row["confluence"])) if row["confluence"] else "none"
            tags = "".join(f"<span class='zl-chip'>{t}</span>" for t in d.tags)
            card(f"""
              <div style='display:flex;align-items:center;gap:11px'>
                <span class='zl-grade' style='background:{gc}22;color:{gc}'>{g}</span>
                <div style='flex:1'>
                  <div style='font-size:15.5px;font-weight:500'>{SYMBOLS[sym]['mt5']}
                    <span style='color:{side};font-size:12.5px;margin-left:6px'>{d.direction}</span></div>
                  <div class='zl-muted' style='margin-top:2px'>{SYMBOLS[sym]['name']} ·
                    {SYMBOLS[sym]['class']}</div>
                </div>
                <div style='text-align:right'>
                  <div class='mono' style='font-size:15px'>{d.rr}R</div>
                  <div class='zl-muted'>{d.lots:.2f} lots</div>
                </div>
              </div>
              <div style='font-size:13px;margin-top:9px;line-height:1.45'>{d.headline}</div>
              <div style='margin-top:8px'>{tags}</div>
              <div class='zl-lv'>
                <div><div class='k'>Entry</div><div class='v mono'>{d.entry:,.{dig}f}</div></div>
                <div><div class='k'>Stop</div><div class='v mono' style='color:{DOWN}'>{d.stop_loss:,.{dig}f}</div></div>
                <div><div class='k'>Target</div><div class='v mono' style='color:{UP}'>{d.take_profit:,.{dig}f}</div></div>
                <div><div class='k'>Daily confluence</div><div class='v' style='font-size:12px'>{conf}</div></div>
              </div>""")
            b1, b2, b3 = st.columns(3)
            if b1.button("Open setup", key=f"o{sym}", use_container_width=True):
                st.session_state["symbol"] = sym
                st.rerun()
            if b2.button("Log this pick", key=f"l{sym}", use_container_width=True):
                log_pick(row)
                st.success(f"{sym} logged.")
            if b3.button("Send to Telegram", key=f"t{sym}", use_container_width=True):
                ok, msg = telegram(
                    f"<b>{g}-grade · {SYMBOLS[sym]['mt5']} {d.direction}</b>\n"
                    f"Entry <code>{d.entry:,.{dig}f}</code>\n"
                    f"SL <code>{d.stop_loss:,.{dig}f}</code>\n"
                    f"TP <code>{d.take_profit:,.{dig}f}</code>\n"
                    f"{d.lots:.2f} lots · {d.rr}R\n\n{d.headline}")
                st.success(msg) if ok else st.warning(msg)

        with st.expander(f"Why {len(rows)-len(found)} symbols were passed"):
            for row in [x for x in rows if not x["decision"].taken]:
                d = row["decision"]
                st.markdown(f"<div class='zl-row'><span class='zl-chip'>{row['symbol']}</span>"
                            f"<span style='flex:1;font-size:12.5px'>{d.headline}</span>"
                            f"<span style='color:{DOWN};font-size:11px'>{d.verdict}</span></div>",
                            unsafe_allow_html=True)

    # ── Setup ticket ──
    def _setup():
        sym = st.session_state["symbol"]
        sym = st.selectbox("Symbol", list(SYMBOLS.keys()),
                           index=list(SYMBOLS.keys()).index(sym))
        st.session_state["symbol"] = sym
        row = next((x for x in (scan["rows"] if scan else []) if x["symbol"] == sym), None)
        if row is None:
            with st.spinner(f"Analysing {sym}…"):
                row = analyse(sym, r, st.session_state["td_key"])

        d, meta, dig = row["decision"], SYMBOLS[sym], SYMBOLS[sym]["digits"]
        if not d.taken:
            card(f"<div class='zl-kicker'>{meta['mt5']} · no setup</div>"
                 f"<div style='font-size:15px;margin-top:6px;line-height:1.4'>{d.headline}</div>"
                 f"<div class='zl-muted' style='margin-top:6px'>Stopped by "
                 f"<span style='color:{DOWN}'>{d.verdict}</span></div>")
            checks = "".join(
                f"<div class='zl-row'><span style='color:{UP if c.passed else DOWN};width:14px'>"
                f"{'✓' if c.passed else '✕'}</span><span style='flex:1;font-size:12.5px'>{c.label}</span>"
                f"<span class='zl-muted mono' style='font-size:11px'>{c.value}</span></div>"
                for c in d.checks)
            card(f"<div class='zl-kicker' style='margin-bottom:4px'>Rule checks</div>{checks}")
            return

        risk_pips = pips(sym, abs(d.entry - d.stop_loss))
        rew_pips = pips(sym, abs(d.take_profit - d.entry))
        g, gc = row["grade"], GRADE_COLOR[row["grade"]]

        st.markdown(f"""
        <div class='zl-card' style='border-color:{gc}44'>
          <div style='display:flex;align-items:center;gap:12px'>
            <span class='zl-grade' style='background:{gc}22;color:{gc};width:38px;height:38px;
                  font-size:17px'>{g}</span>
            <div style='flex:1'>
              <div style='font-size:20px;font-weight:500'>{meta['mt5']} ·
                <span style='color:{UP if d.direction=="BUY" else DOWN}'>{d.direction}</span></div>
              <div class='zl-muted'>{meta['name']} · M15 · {d.rr}R</div>
            </div>
          </div>
          <div style='font-size:13.5px;margin-top:11px;line-height:1.5'>{d.headline}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("##### Place this on MT5")
        st.markdown(f"""
        <div class='zl-ticket'>
          Symbol &nbsp;&nbsp;&nbsp; <b>{meta['mt5']}</b><br>
          Type &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b style='color:{UP if d.direction=="BUY" else DOWN}'>
            Market {d.direction}</b><br>
          Volume &nbsp;&nbsp;&nbsp; <b>{d.lots:.2f}</b> lots<br>
          Stop loss &nbsp;<b style='color:{DOWN}'>{d.stop_loss:,.{dig}f}</b>
            <span style='color:{MUTED}'>&nbsp; ({risk_pips:g} pips)</span><br>
          Take profit <b style='color:{UP}'>{d.take_profit:,.{dig}f}</b>
            <span style='color:{MUTED}'>&nbsp; ({rew_pips:g} pips)</span>
        </div>""", unsafe_allow_html=True)

        st.code(f"{meta['mt5']}  {d.direction}  {d.lots:.2f}  "
                f"SL {d.stop_loss:,.{dig}f}  TP {d.take_profit:,.{dig}f}", language=None)
        st.caption("Entry is at market while price sits in the zone. If it has moved away, "
                   "set a limit order at the entry price instead.")

        c1, c2 = st.columns(2)
        if c1.button("Log this pick", use_container_width=True, key="setup_log"):
            log_pick(row)
            st.success("Logged.")
        if c2.button("Send to Telegram", use_container_width=True, key="setup_tg"):
            ok, msg = telegram(
                f"<b>{g}-grade · {meta['mt5']} {d.direction}</b>\n"
                f"Entry <code>{d.entry:,.{dig}f}</code>\nSL <code>{d.stop_loss:,.{dig}f}</code>\n"
                f"TP <code>{d.take_profit:,.{dig}f}</code>\n{d.lots:.2f} lots · {d.rr}R")
            st.success(msg) if ok else st.warning(msg)

        checks = "".join(
            f"<div class='zl-row'><span style='color:{UP if c.passed else DOWN};width:14px'>"
            f"{'✓' if c.passed else '✕'}</span><span style='flex:1;font-size:12.5px'>{c.label}</span>"
            f"<span class='zl-muted mono' style='font-size:11px'>{c.value}</span></div>"
            for c in d.checks)
        card(f"<div class='zl-kicker' style='margin-bottom:4px'>Every rule checked</div>{checks}")

    # ── Chart ──
    def _chart():
        sym = st.session_state["symbol"]
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.markdown(f"##### {SYMBOLS[sym]['mt5']} · M15")
        span = c2.radio("Bars", [60, 120, 200], index=1, horizontal=True,
                        label_visibility="collapsed")
        show_daily = c3.toggle("Daily levels", True)

        row = next((x for x in (scan["rows"] if scan else []) if x["symbol"] == sym), None)
        if row is None:
            with st.spinner("Loading…"):
                row = analyse(sym, r, st.session_state["td_key"])
        st.plotly_chart(chart(row, r, span, show_daily), use_container_width=True,
                        config={"displayModeBar": False, "scrollZoom": True})
        legend = "".join(f"<span class='zl-chip'><span style='color:{c}'>■</span> {t}</span>"
                         for c, t in [(UP, "Support"), (DOWN, "Resistance"),
                                      (A300, "Fair value gap"), (ACCENT, "Order block"),
                                      (FAINT, "Daily levels")])
        st.markdown(f"<div style='margin-top:6px'>{legend}</div>", unsafe_allow_html=True)

    # ── Daily zones ──
    def _daily():
        sym = st.session_state["symbol"]
        row = next((x for x in (scan["rows"] if scan else []) if x["symbol"] == sym), None)
        if row is None:
            with st.spinner("Loading daily candles…"):
                row = analyse(sym, r, st.session_state["td_key"])
        dig, price = SYMBOLS[sym]["digits"], row["price"]
        st.markdown(f"##### {SYMBOLS[sym]['mt5']} · daily map")
        st.markdown(f"<div class='zl-muted' style='margin-bottom:10px'>Levels drawn from "
                    f"daily candles — the map to mark on your chart before anything else. "
                    f"Price now <b class='mono'>{price:,.{dig}f}</b>.</div>",
                    unsafe_allow_html=True)
        if not row["levels"]:
            note("Daily candles unavailable for this symbol right now.", "warn")
            return
        for lv in row["levels"]:
            col = {"resistance": DOWN, "support": UP}.get(lv.kind, FAINT)
            dist = pips(sym, lv.distance(price))
            above = "above" if lv.price > price else "below"
            st.markdown(f"<div class='zl-row'>"
                        f"<span class='zl-chip' style='background:{col}22;color:{col}'>"
                        f"{lv.kind[:3].upper()}</span>"
                        f"<span style='flex:1;font-size:13px'>{lv.name}</span>"
                        f"<span class='mono' style='font-size:13px'>{lv.price:,.{dig}f}</span>"
                        f"<span class='zl-muted mono' style='font-size:11px;width:96px;"
                        f"text-align:right'>{dist:g} pips {above}</span></div>",
                        unsafe_allow_html=True)

    # ── Picks ──
    def _picks():
        rows = picks()
        if not rows:
            note("No picks logged yet. Log one from the Scanner or Setup tab and it "
                 "appears here with its reasoning.", "muted")
            return
        st.dataframe(pd.DataFrame([{
            "When": x["at"][5:16].replace("T", " "), "Symbol": x["mt5"], "Grade": x["grade"],
            "Side": x["direction"], "Entry": x["entry"], "SL": x["sl"], "TP": x["tp"],
            "R:R": x["rr"], "Lots": x["lots"]} for x in rows]),
            use_container_width=True, hide_index=True)
        st.markdown("##### Reasoning")
        for x in rows[:25]:
            with st.expander(f"{x['mt5']} {x['direction']} · {x['grade']} · {x['at'][5:16]}"):
                st.write(x["headline"])
                st.markdown("".join(f"<span class='zl-chip'>{t}</span>" for t in x["tags"]),
                            unsafe_allow_html=True)
                if x["confluence"]:
                    st.markdown(f"<div class='zl-muted' style='margin-top:6px'>Daily "
                                f"confluence: {', '.join(x['confluence'])}</div>",
                                unsafe_allow_html=True)

    # ── News ──
    def _news():
        t1, t2 = st.tabs(["Economic calendar", "Headlines"])
        with t1:
            if cal_err:
                note(f"Live calendar could not load — {cal_err}.", "warn")
            ahead = [e for e in events if e["time"] > now][:14]
            st.markdown(f"<div class='zl-muted' style='margin-bottom:8px'>Setups are marked "
                        f"news-blocked within {r.news_block_minutes} minutes of a high-impact "
                        f"release.</div>", unsafe_allow_html=True)
            if not ahead:
                note("Nothing further scheduled this week.", "muted")
            for e in ahead:
                mins = int((e["time"] - now).total_seconds() // 60)
                when = f"in {mins}m" if mins < 90 else f"{e['time']:%a %H:%M} UTC"
                col = {"high": DOWN, "medium": WARN}.get(e["impact"], FAINT)
                bg = {"high": "rgba(224,123,135,.14)",
                      "medium": "rgba(217,178,106,.14)"}.get(e["impact"], RAISED)
                card(f"<div style='display:flex;align-items:center;gap:10px'>"
                     f"<span class='zl-chip' style='background:{bg};color:{col}'>"
                     f"{(e['impact'][:4] or 'low').upper()}</span>"
                     f"<span class='zl-chip'>{e['currency']}</span>"
                     f"<span style='flex:1;font-size:13px'>{e['title']}</span>"
                     f"<span class='zl-muted mono' style='font-size:11px'>{when}</span></div>"
                     f"<div class='zl-muted' style='margin-top:6px'>Forecast {e['forecast']} · "
                     f"previous {e['previous']}</div>")
        with t2:
            items, err = headlines()
            if err:
                note(err, "warn")
            for h in items:
                card(f"<div style='font-size:13.5px;line-height:1.45'>"
                     f"<a href='{h['link']}' target='_blank'>{h['title']}</a></div>"
                     f"<div class='zl-muted' style='margin-top:4px'>{h['source']} · {h['when']}</div>")

    # ── Rules ──
    def _rules():
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Entry")
            r.require_reversal_candle = st.toggle("Require a reversal candle", r.require_reversal_candle)
            r.require_fvg_unfilled = st.toggle("Fair value gap must be unfilled", r.require_fvg_unfilled)
            r.require_ob_structure = st.toggle("Order block needs BOS", r.require_ob_structure)
            r.accept_choch = st.toggle("Accept CHoCH reversals", r.accept_choch)
            r.min_zone_touches = st.slider("Minimum zone touches", 1, 5, r.min_zone_touches)
            r.min_rr = st.slider("Minimum reward to risk", 1.0, 4.0, r.min_rr, 0.1)
        with c2:
            st.markdown("##### Sizing")
            r.base_lot = st.number_input("Base lot size", 0.01, 5.0, r.base_lot, 0.01, format="%.2f")
            r.risk_percent = st.slider("Risk per trade (%)", 0.5, 5.0, r.risk_percent, 0.5)
            st.markdown("##### Timing")
            r.news_block_minutes = st.slider("News blackout (min)", 0, 120, r.news_block_minutes, 5)
            r.session_filter = st.toggle("Session-aware volatility", r.session_filter)
        st.session_state["rules"] = r
        st.caption("Re-scan to apply.")

    # ── Alerts ──
    def _alerts():
        st.markdown("##### Telegram alerts")
        note("Streamlit cannot send phone notifications on its own. Telegram can, it is "
             "free, and it takes two minutes.<br>"
             "1 · Message <b>@BotFather</b> on Telegram, send <code>/newbot</code>, copy the token.<br>"
             "2 · Message your new bot once so it may reply.<br>"
             "3 · Message <b>@userinfobot</b> to get your chat id.", "accent")
        st.session_state["tg_token"] = st.text_input("Bot token", st.session_state["tg_token"],
                                                     type="password")
        st.session_state["tg_chat"] = st.text_input("Chat id", st.session_state["tg_chat"])
        if st.button("Send a test message"):
            ok, msg = telegram("<b>Zonelock</b>\nAlerts are working.")
            st.success(msg) if ok else st.warning(msg)

        st.markdown("##### Data fallback")
        st.session_state["td_key"] = st.text_input(
            "Twelve Data API key (optional)", st.session_state["td_key"], type="password",
            help="Free key at twelvedata.com. Used only if Yahoo Finance fails.")

        st.markdown("##### Automatic scanning")
        st.markdown(f"<div class='zl-muted'>This page scans when you press the button. "
                    f"For alerts that arrive while the app is closed, run "
                    f"<code>scanner.py</code> on any free scheduler — GitHub Actions, "
                    f"PythonAnywhere, Railway — every 15 minutes. It uses these same "
                    f"rules and pushes to the same Telegram chat.</div>",
                    unsafe_allow_html=True)

    for tab, fn, label in zip(tabs, [_scanner, _setup, _chart, _daily, _picks, _news, _rules, _alerts],
                              ["Scanner", "Setup", "Chart", "Daily zones", "Picks", "News",
                               "Rules", "Alerts"]):
        with tab:
            safe(fn, label)


{"login": face_login, "app": face_app}[st.session_state["stage"]]()
