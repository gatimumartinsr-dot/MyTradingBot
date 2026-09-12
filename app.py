"""
app.py — Zonelock: support & resistance trade scanner.

The pipeline, in order, is the app:

    scan the market → find high-probability setups → analyse across timeframes
    → calculate entry / SL / TP → rank the setup → alert you → record the result

Each tab is one stage. Nothing here touches your broker: Zonelock reads free
market data, applies your rules, and hands you the order to place yourself.

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
import streamlit.components.v1 as components

import visuals as viz
from backtest import run as backtest_run, sweep as backtest_sweep
from market import (MTF_LADDER, SYMBOLS, TIMEFRAMES, DataError, cache_age,
                    fetch, pips, spread_note)
from setups import (BAND_COLOR, WEIGHTS, build_plan, currency_strength,
                    find_liquidity, range_state, rsi, session_levels)
from strategy import (Rules, atr, build_zones, calculate_lot_size, confluence,
                      daily_zones, evaluate, explain, find_fvgs, mtf_grade,
                      multi_timeframe, order_blocks, reversal_watch)
from tradingview import TV_SYMBOLS, advanced_chart, ticker_tape

PICKS = os.environ.get("ZONELOCK_PICKS", "picks.jsonl")
PROFILE = os.environ.get("ZONELOCK_PROFILE", "profile.json")

BG, SURFACE, RAISED = "#161826", "#1e2030", "#252838"
TEXT, MUTED, FAINT = "#e9e9ed", "#9397ab", "#5f6376"
ACCENT, A300, A700, A800 = "#9184d9", "#d2cefd", "#5d5294", "#3a3360"
UP, DOWN, WARN, INFO = "#5fbf8f", "#e07b87", "#d9b26a", "#6ba4f0"
LINE = "rgba(233,233,237,.10)"
GRADE = {"A": UP, "B": A300, "C": WARN, "—": FAINT}
ORIGIN_COLOR = {"binance": UP, "twelvedata": UP, "stooq": A300,
                "yahoo": A300, "cache": WARN, "demo": DOWN}

CLOCKS = [("Nairobi", 3), ("London", 1), ("New York", -4), ("Tokyo", 9)]
SESSIONS = [("Tokyo", 0, 9), ("London", 7, 16), ("New York", 12, 21)]

st.set_page_config(page_title="Zonelock", layout="wide", page_icon="◈",
                   initial_sidebar_state="collapsed")

st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Zonelock">
<meta name="theme-color" content="#161826">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [data-testid='stAppViewContainer'], [data-testid='stMain'] {{
      background:{BG} !important; color:{TEXT} !important;
      font-family:Inter, system-ui, sans-serif; -webkit-font-smoothing:antialiased; }}
  [data-testid='stHeader'], [data-testid='stToolbar'], [data-testid='stDecoration'],
  [data-testid='stStatusWidget'] {{ display:none !important; height:0 !important; }}
  [data-testid='stSidebar'] {{ background:{SURFACE} !important; border-right:1px solid {LINE}; }}
  .block-container {{ padding:0.7rem 1.1rem 4rem !important; max-width:1500px; }}
  @supports (padding: max(0px)) {{
    .block-container {{ padding-left:max(1.1rem, env(safe-area-inset-left)) !important;
        padding-right:max(1.1rem, env(safe-area-inset-right)) !important;
        padding-bottom:max(4rem, env(safe-area-inset-bottom)) !important; }} }}
  #MainMenu, footer {{ visibility:hidden; }}
  ::selection {{ background:{A800}; color:{TEXT}; }}
  *:focus-visible {{ outline:2px solid {ACCENT} !important; outline-offset:2px !important; }}
  h1,h2,h3,h4,h5,h6 {{ font-weight:500 !important; letter-spacing:-.015em; color:{TEXT} !important; }}
  .mono {{ font-family:'JetBrains Mono', ui-monospace, monospace; font-variant-numeric:tabular-nums; }}
  hr {{ border-color:{LINE} !important; }}
  [data-testid='stVerticalBlock'] {{ gap:0.55rem; }}

  /* ── tabs: pinned, scrollable, pill-active ── */
  .stTabs [data-baseweb='tab-list'] {{ position:sticky; top:0; z-index:99; gap:1px;
      background:{BG}; padding:5px 0 0; margin-bottom:12px; border-bottom:1px solid {LINE};
      overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none; }}
  .stTabs [data-baseweb='tab-list']::-webkit-scrollbar {{ display:none; }}
  .stTabs [data-baseweb='tab'] {{ background:transparent !important; color:{MUTED} !important;
      padding:8px 13px !important; font-size:12.5px !important; font-weight:500 !important;
      white-space:nowrap; border-radius:7px 7px 0 0; transition:color .14s ease; }}
  .stTabs [data-baseweb='tab']:hover {{ color:{A300} !important;
      background:rgba(145,132,217,.07) !important; }}
  .stTabs [aria-selected='true'] {{ color:{TEXT} !important; background:{SURFACE} !important;
      border-bottom:2px solid {ACCENT} !important; }}
  .stTabs [data-baseweb='tab-highlight'], .stTabs [data-baseweb='tab-border'] {{ display:none !important; }}

  .stButton>button, .stDownloadButton>button {{ background:transparent !important;
      border:1px solid {ACCENT} !important; color:{A300} !important; border-radius:8px !important;
      font-weight:500 !important; font-size:13px !important; padding:7px 14px !important;
      transition:background .14s ease !important; }}
  .stButton>button:hover {{ background:rgba(145,132,217,.14) !important; color:{A300} !important; }}
  .stButton>button:active {{ background:rgba(145,132,217,.26) !important; }}
  .stButton>button:focus:not(:active) {{ border-color:{ACCENT} !important; color:{A300} !important; }}

  [data-baseweb='radio'] div[aria-checked='true'] {{ background-color:{ACCENT} !important;
      border-color:{ACCENT} !important; }}
  [data-testid='stRadio'] [role='radiogroup'] > label > div:first-child {{ border-color:{FAINT} !important; }}
  [data-testid='stRadio'] input:checked + div {{ background-color:{ACCENT} !important;
      border-color:{ACCENT} !important; }}
  [data-testid='stCheckbox'] [aria-checked='true'], [data-testid='stToggle'] [aria-checked='true'],
  [data-baseweb='checkbox'] span[aria-checked='true'], [data-baseweb='toggle'] div[aria-checked='true'] {{
      background-color:{ACCENT} !important; border-color:{ACCENT} !important; }}
  [data-baseweb='slider'] div[role='slider'] {{ background:{ACCENT} !important;
      box-shadow:none !important; border-color:{ACCENT} !important; }}
  [data-baseweb='slider'] [data-testid='stThumbValue'] {{ color:{A300} !important; }}
  [data-testid='stSliderTickBar'], [data-testid='stTickBar'] {{ display:none !important; }}
  [data-testid='stProgress'] > div > div > div {{ background-color:{ACCENT} !important; }}
  [data-baseweb='tag'] {{ background-color:{A800} !important; color:{A300} !important; }}
  [data-baseweb='tag'] svg {{ fill:{A300} !important; }}
  .stTextInput input, .stNumberInput input, [data-baseweb='select'] > div, [data-baseweb='input'] {{
      background:{RAISED} !important; border-color:{LINE} !important; color:{TEXT} !important;
      border-radius:8px !important; }}
  .stTextInput input:focus {{ border-color:{ACCENT} !important; box-shadow:0 0 0 1px {ACCENT} !important; }}
  [data-testid='stExpander'] {{ background:{SURFACE} !important; border:1px solid {LINE} !important;
      border-radius:9px !important; }}
  a, a:visited {{ color:{A300} !important; text-decoration:none; }}
  a:hover {{ color:{ACCENT} !important; }}
  code {{ background:{RAISED} !important; color:{A300} !important; border-radius:5px; }}
  [data-testid='stDataFrame'] {{ border:1px solid {LINE}; border-radius:9px; overflow:hidden; }}

  /* ── panels, the reference look ── */
  .zp {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:10px;
      overflow:hidden; margin-bottom:9px; }}
  .zp-head {{ display:flex; align-items:center; gap:8px; padding:9px 13px;
      border-bottom:1px solid {LINE}; background:{RAISED}; }}
  .zp-head .t {{ font-size:10.5px; letter-spacing:.13em; text-transform:uppercase;
      font-weight:600; color:{TEXT}; }}
  .zp-head .r {{ margin-left:auto; font-size:10px; color:{MUTED}; }}
  .zp-body {{ padding:11px 13px; }}
  .zp-flush {{ padding:0; }}

  .zt {{ width:100%; border-collapse:collapse; font-size:11.5px; }}
  .zt th {{ text-align:left; padding:7px 10px; font-size:9px; letter-spacing:.1em;
      text-transform:uppercase; color:{FAINT}; font-weight:600;
      border-bottom:1px solid {LINE}; white-space:nowrap; }}
  .zt td {{ padding:7px 10px; border-bottom:1px solid rgba(233,233,237,.055);
      white-space:nowrap; }}
  .zt tr:last-child td {{ border-bottom:none; }}
  .zt tr:hover td {{ background:rgba(145,132,217,.05); }}
  .zt .num {{ font-family:'JetBrains Mono', monospace; font-variant-numeric:tabular-nums; }}

  .zl-stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:11px; }}
  .zl-stat {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:9px; padding:10px 12px; }}
  .zl-stat .k {{ font-size:9px; letter-spacing:.11em; text-transform:uppercase; color:{FAINT}; }}
  .zl-stat .v {{ font-size:19px; font-weight:500; margin-top:3px; letter-spacing:-.015em; }}
  .zl-stat .s {{ font-size:10px; color:{MUTED}; margin-top:2px; }}
  .zl-chip {{ display:inline-block; font-size:9.5px; letter-spacing:.05em; padding:2.5px 8px;
      border-radius:5px; background:{RAISED}; color:{TEXT}; margin-right:4px;
      margin-bottom:3px; white-space:nowrap; }}
  .zl-muted {{ color:{MUTED}; font-size:11.5px; line-height:1.55; }}
  .zl-row {{ display:flex; align-items:center; gap:9px; padding:8px 0;
      border-bottom:1px solid {LINE}; }}
  .zl-row:last-child {{ border-bottom:none; }}
  .zl-lv {{ display:grid; grid-template-columns:repeat(4,1fr); gap:9px; margin-top:10px;
      padding-top:10px; border-top:1px solid {LINE}; }}
  .zl-lv .k {{ font-size:8.5px; letter-spacing:.1em; text-transform:uppercase; color:{FAINT}; }}
  .zl-lv .v {{ font-size:14px; margin-top:2px; }}
  .zl-grade {{ width:28px; height:28px; border-radius:7px; display:inline-flex;
      align-items:center; justify-content:center; font-size:13px; font-weight:600; flex:none; }}
  .zl-ticket {{ background:{RAISED}; border:1px dashed {ACCENT}; border-radius:9px;
      padding:12px 14px; font-family:'JetBrains Mono', monospace; font-size:12px; line-height:1.95; }}
  .zl-tf {{ display:grid; grid-template-columns:repeat(4,1fr); gap:7px; }}
  .zl-tfc {{ background:{RAISED}; border-radius:8px; padding:9px 10px; }}
  .zl-tfc .tf {{ font-size:10px; letter-spacing:.1em; color:{FAINT}; }}
  .zl-tfc .bias {{ font-size:14px; font-weight:500; margin-top:2px; }}
  .zl-bar {{ height:5px; border-radius:3px; background:{RAISED}; overflow:hidden; margin-top:7px; }}
  .zl-why {{ display:flex; gap:9px; align-items:flex-start; padding:6px 0; }}
  .zl-why .n {{ width:17px; height:17px; border-radius:5px; background:{A800}; color:{A300};
      font-size:9.5px; display:inline-flex; align-items:center; justify-content:center;
      flex:none; margin-top:1px; font-weight:600; }}
  .zl-pipe {{ display:flex; align-items:center; gap:5px; flex-wrap:wrap; font-size:9.5px;
      letter-spacing:.06em; text-transform:uppercase; color:{FAINT}; margin:2px 0 9px; }}
  .zl-pipe b {{ color:{A300}; font-weight:600; }}
  .zl-clock {{ display:flex; gap:14px; flex-wrap:wrap; }}
  .zl-clock .c .n {{ font-size:9px; letter-spacing:.08em; color:{FAINT};
      text-transform:uppercase; }}
  .zl-clock .c .v {{ font-family:'JetBrains Mono', monospace; font-size:13.5px; margin-top:1px; }}

  @media (max-width:900px) {{
      .block-container {{ padding:0.5rem 0.6rem 4rem !important; }}
      .zl-stats {{ grid-template-columns:repeat(2,1fr); gap:6px; }}
      .zl-stat {{ padding:8px 10px; }} .zl-stat .v {{ font-size:16px; }}
      .zl-tf {{ grid-template-columns:repeat(2,1fr); }}
      .zl-lv {{ grid-template-columns:repeat(2,1fr); }}
      .stTabs [data-baseweb='tab'] {{ padding:7px 9px !important; font-size:11.5px !important; }}
      [data-testid='column'] {{ min-width:100% !important; }}
      .zl-clock {{ gap:10px; }} .zl-clock .c .v {{ font-size:12px; }}
      .zt {{ font-size:11px; }} .zt td, .zt th {{ padding:6px 7px; }}
  }}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────────────

PRESETS = {
    "Careful": dict(risk_percent=1.0, min_rr=2.0, min_zone_touches=3,
                    require_reversal_candle=True, require_fvg_unfilled=True,
                    require_ob_structure=True, news_block_minutes=45),
    "Balanced": dict(risk_percent=2.0, min_rr=1.5, min_zone_touches=2,
                     require_reversal_candle=True, require_fvg_unfilled=True,
                     require_ob_structure=True, news_block_minutes=30),
    "Bold": dict(risk_percent=3.0, min_rr=1.3, min_zone_touches=1,
                 require_reversal_candle=True, require_fvg_unfilled=False,
                 require_ob_structure=False, news_block_minutes=15),
}

DEFAULTS = {
    "stage": "login", "user": "", "email": "", "rules": Rules(),
    "symbol": "BTCUSD", "tf": "M15", "scan": None, "scanned_at": None,
    "tg_token": "", "tg_chat": "", "td_key": "", "account_size": 1000.0,
    "watch": ["BTCUSD", "ETHUSD", "XAUUSD", "EURUSD", "GBPUSD", "NAS100"],
    "ladder": list(MTF_LADDER), "preset": "Balanced", "engine": "Zonelock",
    "tape": True, "notes": "", "beginner": True, "plan_open": None,
    "min_score": 60,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def panel(title: str, body: str, right: str = "", flush: bool = False):
    cls = "zp-body zp-flush" if flush else "zp-body"
    st.markdown(f"<div class='zp'><div class='zp-head'><span class='t'>{title}</span>"
                f"<span class='r'>{right}</span></div>"
                f"<div class='{cls}'>{body}</div></div>", unsafe_allow_html=True)


def card(html: str):
    st.markdown(f"<div class='zp'><div class='zp-body'>{html}</div></div>",
                unsafe_allow_html=True)


def note(text: str, tone: str = "muted"):
    color = {"muted": MUTED, "warn": WARN, "up": UP, "down": DOWN, "accent": A300}[tone]
    edge = {"muted": LINE, "warn": "rgba(217,178,106,.35)", "up": "rgba(95,191,143,.3)",
            "down": "rgba(224,123,135,.35)", "accent": "rgba(145,132,217,.35)"}[tone]
    st.markdown(f"<div style='background:{SURFACE};border:1px solid {edge};border-radius:9px;"
                f"padding:11px 13px;font-size:12px;color:{color};line-height:1.55;"
                f"margin-bottom:9px'>{text}</div>", unsafe_allow_html=True)


def explainer(title: str, svg: str, body: str):
    st.markdown(f"<div class='zp'><div class='zp-head'><span class='t'>{title}</span></div>"
                f"<div class='zp-body'>{svg}"
                f"<div class='zl-muted' style='margin-top:9px'>{body}</div></div></div>",
                unsafe_allow_html=True)


def _get(url: str, timeout: int = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Zonelock)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def save_profile():
    r: Rules = st.session_state["rules"]
    try:
        with open(PROFILE, "w", encoding="utf-8") as f:
            json.dump({"rules": {k: getattr(r, k) for k in r.__dataclass_fields__
                                 if not isinstance(getattr(r, k), tuple)},
                       "watch": st.session_state["watch"],
                       "ladder": st.session_state["ladder"], "tf": st.session_state["tf"],
                       "account_size": st.session_state["account_size"],
                       "preset": st.session_state["preset"],
                       "beginner": st.session_state["beginner"],
                       "notes": st.session_state["notes"]}, f, indent=2)
        return True
    except Exception:
        return False


def load_profile():
    try:
        with open(PROFILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    r = Rules()
    for k, v in (data.get("rules") or {}).items():
        if hasattr(r, k):
            setattr(r, k, v)
    st.session_state["rules"] = r
    for key in ("watch", "ladder", "tf", "account_size", "preset", "beginner", "notes"):
        if key in data:
            st.session_state[key] = data[key]
    return True


def apply_preset(name: str):
    r: Rules = st.session_state["rules"]
    for k, v in PRESETS[name].items():
        setattr(r, k, v)
    st.session_state.update(rules=r, preset=name)


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
    for src, url in [("Investing.com", "https://www.investing.com/rss/news_1.rss"),
                     ("FXStreet", "https://www.fxstreet.com/rss/news"),
                     ("Reuters", "https://feeds.reuters.com/reuters/businessNews")]:
        try:
            root = ET.fromstring(_get(url))
            items = []
            for it in root.iter("item"):
                t = (it.findtext("title") or "").strip()
                if t:
                    items.append({"title": t, "link": (it.findtext("link") or "").strip(),
                                  "when": (it.findtext("pubDate") or "")[:22], "source": src})
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


def telegram(text: str):
    tok, chat = st.session_state["tg_token"], st.session_state["tg_chat"]
    if not (tok and chat):
        return False, "Telegram not set up — see Settings."
    try:
        url = (f"https://api.telegram.org/bot{tok}/sendMessage?chat_id={chat}"
               f"&parse_mode=HTML&text={urllib.parse.quote(text)}")
        ok = json.loads(_get(url).decode()).get("ok", False)
        return ok, "Sent." if ok else "Telegram rejected the message."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


# ── analysis ─────────────────────────────────────────────────────────

def _news_for(symbol: str):
    """Minutes until the next high-impact event that touches this symbol."""
    events, _ = economic_calendar()
    now = datetime.now(timezone.utc)
    sym = symbol.upper()
    for e in events:
        if e["impact"] != "high" or e["time"] < now:
            continue
        cur = e["currency"]
        if cur in sym or (cur == "USD" and any(
                k in sym for k in ("XAU", "US30", "NAS", "SPX", "OIL", "BTC", "ETH"))):
            return int((e["time"] - now).total_seconds() // 60), e["title"]
    return None, ""


def analyse(symbol: str, rules: Rules, td_key: str, ladder=None, base=None) -> dict:
    ladder = ladder or st.session_state["ladder"]
    base = base or st.session_state["tf"]
    frames, origins = {}, {}
    for tf in dict.fromkeys([base, *ladder]):
        try:
            df, origin = fetch(symbol, tf, 400, td_key)
            frames[tf], origins[tf] = df, origin
        except Exception:
            continue
    if base not in frames:
        raise DataError(f"{symbol} {base} unavailable from every source")

    primary = frames[base]
    price = float(primary["close"].iloc[-1])
    a = atr(primary, 14)
    d1 = frames.get("D1")
    if d1 is None:
        try:
            d1, _ = fetch(symbol, "D1", 200, td_key)
        except Exception:
            d1 = None
    levels = daily_zones(d1, price) if d1 is not None else []

    view = multi_timeframe(frames, rules)
    dec = evaluate(symbol, primary, balance=st.session_state["account_size"],
                   tick_value=1.0, tick_size=SYMBOLS[symbol]["pip"], rules=rules)
    conf = confluence(dec, levels, a) if dec.taken else []
    watch = None if dec.taken else reversal_watch(
        symbol, primary, TIMEFRAMES[base]["minutes"], rules)

    prev = float(primary["close"].iloc[-96]) if len(primary) > 96 else float(primary["close"].iloc[0])
    change = (price - prev) / prev * 100 if prev else 0.0
    zones = build_zones(primary, rules)
    sups = [z for z in zones if z.kind == "support"]
    ress = [z for z in zones if z.kind == "resistance"]

    news_mins, news_title = _news_for(symbol)
    plan = build_plan(symbol, SYMBOLS[symbol]["mt5"], SYMBOLS[symbol]["digits"], dec,
                      primary, view, conf, rules, timeframe=base,
                      news_minutes=news_mins, news_title=news_title,
                      reasons=explain(dec, view, conf, symbol))
    vol_state, vol_ratio = range_state(primary)

    return {"symbol": symbol, "tf": base, "decision": dec, "price": price, "atr": a,
            "change": change, "levels": levels, "confluence": conf, "view": view,
            "grade": mtf_grade(dec, view, conf), "frames": frames, "origins": origins,
            "origin": origins.get(base, "demo"), "primary": primary, "d1": d1,
            "watch": watch, "why": explain(dec, view, conf, symbol),
            "plan": plan, "score": plan.score if plan else None,
            "liquidity": plan.liquidity if plan else find_liquidity(primary, rules),
            "rsi": rsi(primary), "vol_state": vol_state, "vol_ratio": vol_ratio,
            "sessions": session_levels(primary),
            "support": max([z for z in sups if z.mid <= price] or sups,
                           key=lambda z: z.mid, default=None),
            "resistance": min([z for z in ress if z.mid >= price] or ress,
                              key=lambda z: z.mid, default=None)}


def run_scan(rules: Rules):
    out, failed = [], []
    watch = st.session_state["watch"]
    bar = st.progress(0.0, text="Scanning the market…")
    for i, sym in enumerate(watch, 1):
        bar.progress(i / len(watch), text=f"{sym} · {' · '.join(st.session_state['ladder'])}")
        try:
            out.append(analyse(sym, rules, st.session_state["td_key"]))
        except Exception as exc:
            failed.append(f"{sym}: {exc}")
    bar.empty()
    out.sort(key=lambda r: (-(r["score"].total if r.get("score") else -1),
                            -(r["decision"].rr or 0)))
    st.session_state["scan"] = {"rows": out, "failed": failed}
    st.session_state["scanned_at"] = datetime.now(timezone.utc)


def cached_row(symbol: str, rules: Rules):
    scan = st.session_state["scan"]
    hit = next((x for x in (scan["rows"] if scan else [])
                if x["symbol"] == symbol and x["tf"] == st.session_state["tf"]), None)
    if hit:
        return hit
    with st.spinner(f"Analysing {symbol}…"):
        return analyse(symbol, rules, st.session_state["td_key"])


def log_pick(row: dict, outcome: str = "pending"):
    d, sym = row["decision"], row["symbol"]
    with open(PICKS, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "at": datetime.now(timezone.utc).isoformat(), "symbol": sym,
            "mt5": SYMBOLS[sym]["mt5"], "tf": row["tf"], "grade": row["grade"],
            "direction": d.direction, "entry": d.entry, "sl": d.stop_loss,
            "tp": d.take_profit, "rr": d.rr, "lots": d.lots,
            "risk_pips": pips(sym, abs(d.entry - d.stop_loss)),
            "reward_pips": pips(sym, abs(d.take_profit - d.entry)),
            "headline": d.headline, "tags": d.tags, "why": row["why"],
            "confluence": row["confluence"], "alignment": row["view"].alignment,
            "origin": row["origin"], "outcome": outcome}) + "\n")


def picks(limit: int = 300):
    if not os.path.exists(PICKS):
        return []
    with open(PICKS, encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return rows[-limit:][::-1]


def ticket_text(row: dict) -> str:
    d, sym = row["decision"], row["symbol"]
    dig = SYMBOLS[sym]["digits"]
    rp = pips(sym, abs(d.entry - d.stop_loss))
    wp = pips(sym, abs(d.take_profit - d.entry))
    body = (f"<b>{row['grade']}-grade · {SYMBOLS[sym]['mt5']} {d.direction}</b>\n"
            f"{row['tf']} · stack {row['view'].alignment}\n\n"
            f"Entry <code>{d.entry:,.{dig}f}</code>\n"
            f"SL <code>{d.stop_loss:,.{dig}f}</code> ({rp:g} pips)\n"
            f"TP <code>{d.take_profit:,.{dig}f}</code> ({wp:g} pips)\n"
            f"{d.lots:.2f} lots · {d.rr}R\n\nWhy:\n")
    return body + "\n".join(f"• {w}" for w in row["why"][:4])


def origin_chip(origin: str) -> str:
    c = ORIGIN_COLOR.get(origin, FAINT)
    return f"<span class='zl-chip' style='background:{c}22;color:{c}'>{origin.upper()}</span>"


def score_pill(row: dict) -> str:
    sc = row.get("score")
    if not sc or not row["decision"].taken:
        return "<span class='zl-chip'>—</span>"
    return (f"<span class='zl-chip' style='background:{sc.color}22;color:{sc.color};"
            f"font-weight:600'>{sc.band} · {sc.total}%</span>")


def state_of(row: dict):
    sc = row.get("score")
    if row["decision"].taken:
        return (sc.band if sc else "SETUP"), (sc.color if sc else UP)
    if row.get("watch"):
        return row["watch"].urgency.upper(), WARN
    return "—", FAINT


# ── chart ────────────────────────────────────────────────────────────

def chart(row: dict, rules: Rules, bars: int = 120, show_daily: bool = True,
          height: int = 420) -> go.Figure:
    symbol, df = row["symbol"], row["primary"]
    dig = SYMBOLS[symbol]["digits"]
    gaps = [g for g in find_fvgs(df, rules) if not g.filled]
    blocks = order_blocks(df, rules)

    view = df.iloc[-bars:].reset_index(drop=True)
    price = float(view["close"].iloc[-1])
    lo_v, hi_v = float(view["low"].min()), float(view["high"].max())
    pad = (hi_v - lo_v) * 0.10
    y_lo, y_hi = lo_v - pad, hi_v + pad
    t0, t1 = view["time"].iloc[0], view["time"].iloc[-1]
    step = view["time"].iloc[1] - view["time"].iloc[0]
    right = t1 + step * 2

    fig = go.Figure(go.Candlestick(
        x=view["time"], open=view["open"], high=view["high"], low=view["low"],
        close=view["close"], increasing_line_color=UP, decreasing_line_color=DOWN,
        increasing_fillcolor=UP, decreasing_fillcolor=DOWN, line_width=1,
        whiskerwidth=0.15, showlegend=False))

    drawn = []

    def level(value, color, label, dash="dash", width=1.5):
        if value is None or not (y_lo < value < y_hi):
            return
        for v in drawn:
            if abs(v - value) < (y_hi - y_lo) * 0.024:
                return
        drawn.append(value)
        fig.add_shape(type="line", x0=t0, x1=right, y0=value, y1=value,
                      line=dict(color=color, width=width, dash=dash))
        fig.add_annotation(x=right, y=value, text=f"{label} {value:,.{dig}f}",
                           showarrow=False, xanchor="right", yanchor="bottom", yshift=3,
                           font=dict(size=10.5, color=color,
                                     family="JetBrains Mono, monospace"))

    def zone(lo, hi, fill):
        fig.add_shape(type="rect", x0=t0, x1=right, y0=lo, y1=hi, fillcolor=fill,
                      layer="below", line=dict(width=0))

    d = row["decision"]
    if d.taken:
        zone(min(d.entry, d.take_profit), max(d.entry, d.take_profit), f"rgba(95,191,143,.07)")
        zone(min(d.entry, d.stop_loss), max(d.entry, d.stop_loss), f"rgba(224,123,135,.07)")
        level(d.entry, INFO, "ENTRY", "solid", 1.6)
        level(d.stop_loss, DOWN, "SL")
        level(d.take_profit, UP, "TP")

    for ob in blocks[:1]:
        zone(ob.low, ob.high, "rgba(217,178,106,.10)")
        level((ob.low + ob.high) / 2, WARN, "OB", "dash", 1.2)
    for g in gaps[-1:]:
        zone(g.low, g.high, "rgba(145,132,217,.12)")
        level((g.low + g.high) / 2, A300, "FVG", "dot", 1.2)

    if row.get("support"):
        zone(row["support"].low, row["support"].high, "rgba(95,191,143,.09)")
        level(row["support"].mid, UP, "SUPPORT", "dash", 1.2)
    if row.get("resistance"):
        zone(row["resistance"].low, row["resistance"].high, "rgba(224,123,135,.09)")
        level(row["resistance"].mid, DOWN, "RESISTANCE", "dash", 1.2)
    if show_daily:
        for lv in row["levels"][:3]:
            level(lv.price, FAINT, lv.name.upper(), "dot", 1)

    fig.add_annotation(x=t1, y=price, text=f" {price:,.{dig}f} ", showarrow=False,
                       xanchor="left", yanchor="middle", bgcolor=A300, borderpad=3,
                       font=dict(size=10, color=BG, family="JetBrains Mono, monospace"))

    fig.update_layout(
        height=height, margin=dict(l=4, r=8, t=4, b=4), dragmode="pan",
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, showlegend=False,
        font=dict(color=MUTED, family="JetBrains Mono, monospace", size=10),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=RAISED, bordercolor=LINE,
                        font=dict(color=TEXT, family="Inter", size=11)),
        xaxis=dict(rangeslider_visible=False, gridcolor="rgba(233,233,237,.05)",
                   showline=False, zeroline=False, range=[t0, right], tickformat="%H:%M",
                   showspikes=True, spikemode="across", spikesnap="cursor",
                   spikethickness=1, spikedash="dot", spikecolor="rgba(233,233,237,.2)"),
        yaxis=dict(gridcolor="rgba(233,233,237,.06)", side="left", zeroline=False,
                   range=[y_lo, y_hi], tickformat=f",.{dig}f", showline=False))
    return fig


def price_header(row: dict):
    sym, d = row["symbol"], row["decision"]
    meta = SYMBOLS[sym]
    dig = meta["digits"]
    c = UP if row["change"] >= 0 else DOWN
    v = row["view"]
    state, scol = state_of(row)
    bits = [f"{d.direction} SETUP"] if d.taken else (
        [f"{row['watch'].direction} FORMING"] if row.get("watch") else [])
    for tf, rd in v.reads.items():
        if rd.structure != "none":
            bits.append(f"{rd.structure} {tf}")
            break
    if sum(rd.unfilled_fvgs for rd in v.reads.values()):
        bits.append("FVG OPEN")
    st.markdown(f"""
    <div style='padding:0 0 8px'>
      <div style='display:flex;align-items:baseline;gap:9px;flex-wrap:wrap'>
        <span style='font-size:26px;font-weight:600;letter-spacing:-.02em'>{sym}</span>
        <span class='zl-muted'>{meta['mt5']} · {meta['name']} · {row['tf']}</span>
        <span style='margin-left:auto'>{origin_chip(row['origin'])}</span>
      </div>
      <div style='display:flex;align-items:baseline;gap:11px;margin-top:1px'>
        <span class='mono' style='font-size:34px;font-weight:500;letter-spacing:-.03em;
              line-height:1.05'>{row['price']:,.{dig}f}</span>
        <span class='mono' style='font-size:15px;color:{c}'>{row['change']:+.2f}%</span>
        <span class='zl-chip' style='background:{scol}22;color:{scol};margin-left:4px'>
          {"  •  ".join(bits) or "NO SIGNAL"}</span>
      </div>
    </div>""", unsafe_allow_html=True)


def mtf_panel(row: dict):
    view = row["view"]
    col = {"bullish": UP, "bearish": DOWN}.get(view.alignment, WARN)
    cells = ""
    for tf in ["M5", "M15", "M30", "H1", "H4", "D1", "W1"]:
        rd = view.reads.get(tf)
        if not rd:
            continue
        c = {"bullish": UP, "bearish": DOWN}.get(rd.bias, FAINT)
        bits = [b for b in [rd.structure if rd.structure != "none" else "",
                            f"at {rd.at_zone}" if rd.at_zone != "mid-range" else "",
                            rd.reversal or "",
                            f"{rd.unfilled_fvgs} FVG" if rd.unfilled_fvgs else ""] if b]
        cells += (f"<div class='zl-tfc'><div class='tf'>{tf}</div>"
                  f"<div class='bias' style='color:{c}'>{rd.bias}</div>"
                  f"<div class='zl-muted' style='margin-top:3px;font-size:10px'>"
                  f"{' · '.join(bits) or 'no signal'}</div></div>")
    pct = int(view.agreement * 100)
    panel("Timeframe agreement",
          f"<div class='zl-tf'>{cells}</div>"
          f"<div class='zl-bar'><div style='width:{pct}%;height:100%;background:{col}'></div></div>"
          f"<div class='zl-muted' style='margin-top:7px'>{view.summary}</div>",
          f"<span style='color:{col}'>{view.alignment.upper()} · {pct}%</span>")


def why_block(row: dict):
    if not row["why"]:
        return
    items = "".join(f"<div class='zl-why'><span class='n'>{i}</span>"
                    f"<span style='flex:1;font-size:12px;line-height:1.5'>{w}</span></div>"
                    for i, w in enumerate(row["why"], 1))
    panel("Why this trade was picked", items)


def watch_card(w, symbol: str):
    dig = SYMBOLS[symbol]["digits"]
    col = {"imminent": UP, "watching": WARN}.get(w.urgency, FAINT)
    side = UP if w.direction == "BUY" else DOWN
    forming = (f"<div style='margin-top:6px;font-size:11.5px;color:{UP}'>"
               f"◆ Candle forming now: {w.forming}</div>") if w.forming else ""
    panel("Not confirmed yet",
          f"<div style='display:flex;align-items:center;gap:9px'>"
          f"<span class='zl-chip' style='background:{col}22;color:{col}'>{w.urgency.upper()}</span>"
          f"<span style='font-size:14px;font-weight:500'>{SYMBOLS[symbol]['mt5']}</span>"
          f"<span style='color:{side};font-size:11.5px'>{w.direction} forming</span>"
          f"<span style='margin-left:auto' class='zl-muted mono'>"
          f"{pips(symbol, w.distance):g} pips away</span></div>"
          f"<div style='font-size:12px;margin-top:7px;line-height:1.5'>Price is {w.state} "
          f"at the {w.zone_kind} <span class='mono'>{w.zone_low:,.{dig}f}–"
          f"{w.zone_high:,.{dig}f}</span>. Waiting for {w.waiting_for}.</div>{forming}"
          f"<div class='zl-muted' style='margin-top:6px'>Candle closes in about "
          f"{w.minutes_left} min</div>")


def setup_card(row: dict, key_prefix: str = ""):
    d, sym = row["decision"], row["symbol"]
    dig, g, gc = SYMBOLS[sym]["digits"], row["grade"], GRADE[row["grade"]]
    side = UP if d.direction == "BUY" else DOWN
    v = row["view"]
    al = UP if v.agrees_with(d.direction) else (WARN if v.alignment == "mixed" else DOWN)
    rp = pips(sym, abs(d.entry - d.stop_loss))
    wp = pips(sym, abs(d.take_profit - d.entry))
    risk_cash = st.session_state["account_size"] * st.session_state["rules"].risk_percent / 100
    tags = "".join(f"<span class='zl-chip'>{t}</span>" for t in d.tags)
    st.markdown(f"""
    <div class='zp'>
      <div class='zp-head'>
        <span class='zl-grade' style='background:{gc}22;color:{gc}'>{g}</span>
        <span class='t' style='letter-spacing:.04em;font-size:13px;text-transform:none'>
          {SYMBOLS[sym]['mt5']}</span>
        <span class='zl-chip' style='background:{side}22;color:{side}'>{d.direction}</span>
        <span class='r'>{row['tf']} · {viz.confidence_bar(g)}</span>
      </div>
      <div class='zp-body'>
        <div style='font-size:12.5px;line-height:1.5'>{d.headline}</div>
        <div style='margin-top:8px'>{tags}
          <span class='zl-chip' style='background:{al}22;color:{al}'>
            stack {v.alignment} {int(v.agreement*100)}%</span>{origin_chip(row['origin'])}</div>
        <div class='zl-lv'>
          <div><div class='k'>Entry</div><div class='v mono'>{d.entry:,.{dig}f}</div></div>
          <div><div class='k'>Stop · {rp:g} pips</div>
            <div class='v mono' style='color:{DOWN}'>{d.stop_loss:,.{dig}f}</div></div>
          <div><div class='k'>Target · {wp:g} pips</div>
            <div class='v mono' style='color:{UP}'>{d.take_profit:,.{dig}f}</div></div>
          <div><div class='k'>Size · {d.rr}R</div><div class='v mono'>{d.lots:.2f} lots</div></div>
        </div>
        <div class='zl-muted' style='margin-top:8px'>Risking
          <b style='color:{DOWN}'>${risk_cash:,.2f}</b> to make
          <b style='color:{UP}'>${risk_cash * (d.rr or 0):,.2f}</b>.
          {' · '.join(row['confluence']) if row['confluence'] else ''}</div>
      </div>
    </div>""", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    if b1.button("Open", key=f"{key_prefix}o{sym}", use_container_width=True):
        st.session_state.update(symbol=sym)
        st.rerun()
    if b2.button("Log pick", key=f"{key_prefix}l{sym}", use_container_width=True):
        log_pick(row)
        st.success(f"{sym} recorded in the journal.")
    if b3.button("Alert me", key=f"{key_prefix}t{sym}", use_container_width=True):
        ok, msg = telegram(ticket_text(row))
        st.success(msg) if ok else st.warning(msg)


def score_panel(row: dict):
    """The 0-100 score with every point attributed."""
    sc = row.get("score")
    if not sc:
        return
    bars = ""
    for f in sc.factors:
        col = UP if f.pct >= 80 else (A300 if f.pct >= 50 else
                                      (WARN if f.pct > 0 else FAINT))
        bars += (f"<div class='zl-row' style='padding:6px 0'>"
                 f"<span style='flex:1;font-size:11.5px'>{f.name}</span>"
                 f"<span class='zl-muted' style='font-size:10.5px;flex:2;"
                 f"text-align:right;padding-right:8px'>{f.detail}</span>"
                 f"{viz.strength_bar(int(f.pct), col, 52)}"
                 f"<span class='mono' style='font-size:10.5px;width:40px;"
                 f"text-align:right;color:{col}'>{f.earned}/{f.weight}</span></div>")
    if sc.news_penalty:
        bars += (f"<div class='zl-row' style='padding:6px 0'>"
                 f"<span style='flex:1;font-size:11.5px;color:{DOWN}'>News risk</span>"
                 f"<span class='zl-muted' style='font-size:10.5px;flex:2;"
                 f"text-align:right;padding-right:8px'>{sc.news_note}</span>"
                 f"<span class='mono' style='font-size:10.5px;color:{DOWN}'>"
                 f"−{sc.news_penalty}</span></div>")
    panel("Confidence — where every point came from", bars,
          f"<span style='color:{sc.color};font-weight:600'>{sc.total}% · {sc.band}</span>")


def plan_card(row: dict, key_prefix: str = "", rank: int = 0):
    """The spec's trade-plan output: zone, staged targets, invalidation."""
    plan = row.get("plan")
    if plan is None:
        return
    sc, d = plan.score, plan.digits
    side = UP if plan.direction == "BUY" else DOWN
    v = row["view"]
    risk_cash = st.session_state["account_size"] * st.session_state["rules"].risk_percent / 100
    win_cash = risk_cash * plan.rr2
    tags = "".join(f"<span class='zl-chip'>{t}</span>" for t in row["decision"].tags)
    rank_badge = (f"<span class='zl-grade' style='background:{RAISED};color:{MUTED};"
                  f"font-size:11px'>{rank}</span>") if rank else ""
    warn = (f"<br><b style='color:{WARN}'>⚠ {plan.news_warning}</b>"
            if plan.news_warning else "")

    head = (f"<div class='zp-head'>{rank_badge}"
            f"<span class='zl-grade' style='background:{sc.color}22;color:{sc.color}'>"
            f"{sc.band}</span>"
            f"<span class='t' style='letter-spacing:.03em;font-size:13.5px;"
            f"text-transform:none'>{plan.mt5}</span>"
            f"<span class='zl-chip' style='background:{side}22;color:{side}'>"
            f"{plan.direction}</span>"
            f"<span class='zl-muted' style='font-size:11px'>{plan.setup_type}</span>"
            f"<span class='r'>{plan.timeframe} &nbsp;"
            f"{viz.strength_bar(sc.total, sc.color, 58)} "
            f"<b style='color:{sc.color}'>{sc.total}%</b></span></div>")

    body = (f"<div class='zp-body'>"
            f"<div style='font-size:12.5px;line-height:1.5'>"
            f"{row['decision'].headline}</div>"
            f"<div style='margin-top:8px'>{tags}"
            f"<span class='zl-chip' style='background:{ACCENT}22;color:{A300}'>"
            f"stack {v.alignment} {int(v.agreement*100)}%</span>"
            f"{origin_chip(row['origin'])}</div>"
            f"<div class='zl-lv'>"
            f"<div><div class='k'>Entry zone</div>"
            f"<div class='v mono' style='font-size:12.5px'>"
            f"{plan.entry_low:,.{d}f}–{plan.entry_high:,.{d}f}</div></div>"
            f"<div><div class='k'>Stop loss</div>"
            f"<div class='v mono' style='color:{DOWN}'>{plan.stop:,.{d}f}</div></div>"
            f"<div><div class='k'>Size</div>"
            f"<div class='v mono'>{plan.lots:.2f} lots</div></div>"
            f"<div><div class='k'>Risking</div>"
            f"<div class='v mono' style='color:{DOWN}'>${risk_cash:,.2f}</div></div>"
            f"</div>"
            f"<div class='zl-lv'>"
            f"<div><div class='k'>TP1 · 1:{plan.rr1:g}</div>"
            f"<div class='v mono' style='color:{UP}'>{plan.tp1:,.{d}f}</div></div>"
            f"<div><div class='k'>TP2 · 1:{plan.rr2:g}</div>"
            f"<div class='v mono' style='color:{UP}'>{plan.tp2:,.{d}f}</div></div>"
            f"<div><div class='k'>TP3 · 1:{plan.rr3:g}</div>"
            f"<div class='v mono' style='color:{UP}'>{plan.tp3:,.{d}f}</div></div>"
            f"<div><div class='k'>At TP2 you make</div>"
            f"<div class='v mono' style='color:{UP}'>${win_cash:,.2f}</div></div>"
            f"</div>"
            f"<div class='zl-muted' style='margin-top:9px;padding-top:9px;"
            f"border-top:1px solid {LINE}'>"
            f"<b style='color:{DOWN}'>Invalid if</b> {plan.invalidation}.{warn}"
            f"</div></div>")

    st.markdown(f"<div class='zp'>{head}{body}</div>", unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4)
    if b1.button("Chart", key=f"{key_prefix}c{plan.symbol}", use_container_width=True):
        st.session_state["symbol"] = plan.symbol
        st.rerun()
    open_now = st.session_state.get("plan_open") == plan.symbol
    if b2.button("Close" if open_now else "Why", key=f"{key_prefix}p{plan.symbol}",
                 use_container_width=True):
        st.session_state["plan_open"] = None if open_now else plan.symbol
        st.rerun()
    if b3.button("Log", key=f"{key_prefix}l{plan.symbol}", use_container_width=True):
        log_pick(row)
        st.success(f"{plan.mt5} recorded in the journal.")
    if b4.button("Alert", key=f"{key_prefix}a{plan.symbol}", use_container_width=True):
        ok, msg = telegram(plan.telegram())
        st.success(msg) if ok else st.warning(msg)

    if open_now:
        score_panel(row)
        why_block(row)
        liq = plan.liquidity
        bs = f"{liq.buyside:,.{d}f}" if liq.buyside else "—"
        ss = f"{liq.sellside:,.{d}f}" if liq.sellside else "—"
        panel("Liquidity",
              f"<div class='zl-muted'>{liq.note}.</div>"
              f"<div class='zl-lv' style='margin-top:8px'>"
              f"<div><div class='k'>Equal highs</div><div class='v mono' "
              f"style='font-size:12.5px'>{len(liq.equal_highs)}</div></div>"
              f"<div><div class='k'>Equal lows</div><div class='v mono' "
              f"style='font-size:12.5px'>{len(liq.equal_lows)}</div></div>"
              f"<div><div class='k'>Buy-side pool</div><div class='v mono' "
              f"style='font-size:12.5px'>{bs}</div></div>"
              f"<div><div class='k'>Sell-side pool</div><div class='v mono' "
              f"style='font-size:12.5px'>{ss}</div></div></div>")
        st.code(f"{plan.mt5}  {plan.direction}  {plan.lots:.2f}   "
                f"entry {plan.entry_low:,.{d}f}-{plan.entry_high:,.{d}f}   "
                f"SL {plan.stop:,.{d}f}   TP1 {plan.tp1:,.{d}f}   "
                f"TP2 {plan.tp2:,.{d}f}   TP3 {plan.tp3:,.{d}f}", language=None)


def safe(fn, label):
    try:
        fn()
    except Exception as exc:
        st.error(f"{label}: {type(exc).__name__} — {exc}")
        with st.expander("Details"):
            import traceback
            st.code(traceback.format_exc())


# ──────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────

def face_login():
    _, mid, _ = st.columns([1, 1.35, 1])
    with mid:
        st.markdown(f"""
        <div style='padding:6vh 0 4px'>
          <div style='letter-spacing:.26em;font-size:11.5px;color:{ACCENT}'>◈ ZONELOCK</div>
          <div style='font-size:31px;font-weight:500;letter-spacing:-.025em;line-height:1.16;
               margin-top:13px'>Finds the level.<br>You place the trade.</div>
          <div class='zl-muted' style='margin-top:11px;max-width:40ch;font-size:12.5px'>
            It watches the prices where the market has turned before, waits for a candle
            to prove it is turning again, then hands you the order — entry, stop, target
            and size — to type into MT5.</div>
        </div>""", unsafe_allow_html=True)

        steps = "".join(
            f"<div style='display:flex;gap:8px;align-items:center;padding:5px 0'>"
            f"<span style='width:5px;height:5px;border-radius:50%;background:{ACCENT}'></span>"
            f"<span style='font-size:12px'>{t}</span></div>"
            for t in ["Scan the market", "Find high-probability setups",
                      "Check every timeframe agrees", "Work out entry, stop and target",
                      "Rank it A, B or C", "Alert you", "Record the result"])
        st.markdown(f"<div class='zp'><div class='zp-head'><span class='t'>How it works"
                    f"</span></div><div class='zp-body'>{steps}</div></div>",
                    unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign in", "Create account"])
        with tab_in:
            email = st.text_input("Email", "martins@zonelock.app", key="li_email")
            pwd = st.text_input("Password", "helix2026", type="password", key="li_pass")
            if st.button("Sign in", use_container_width=True):
                if email and pwd:
                    load_profile()
                    st.session_state.update(email=email, user=email.split("@")[0].title(),
                                            stage="app")
                    st.rerun()
                else:
                    st.error("Enter your email and password.")
        with tab_up:
            name = st.text_input("Full name", key="su_name")
            em2 = st.text_input("Email", key="su_email")
            pw2 = st.text_input("Password", type="password", key="su_pass")
            lvl = st.radio("How much trading have you done?",
                           ["None yet", "Some", "A lot"], index=0, horizontal=True)
            if st.button("Create account", use_container_width=True):
                if name and em2 and len(pw2) >= 6:
                    st.session_state.update(user=name, email=em2, stage="setup",
                                            beginner=lvl != "A lot")
                    st.rerun()
                else:
                    st.error("Name, email and a password of 6+ characters.")

        st.markdown("<div class='zl-muted' style='margin-top:10px'>No broker login needed. "
                    "Zonelock never touches your money.</div>", unsafe_allow_html=True)


def face_setup():
    _, mid, _ = st.columns([1, 1.35, 1])
    with mid:
        st.markdown("<div style='height:4vh'></div>", unsafe_allow_html=True)
        st.progress(1.0, text="Last step")
        st.markdown("## How careful should it be?")
        st.markdown("<div class='zl-muted' style='margin-bottom:10px'>Every rule stays "
                    "editable later. Start careful.</div>", unsafe_allow_html=True)

        chosen = st.radio("Style", list(PRESETS.keys()), index=1, horizontal=True,
                          captions=["1% risk · needs 2× reward", "2% risk · needs 1.5×",
                                    "3% risk · takes more trades"])
        st.session_state["account_size"] = st.number_input(
            "How much is in your trading account? ($)", 50.0, 1_000_000.0,
            st.session_state["account_size"], 50.0, key="ob_acct",
            help="Only used to work out position size. Nothing is connected.")

        r = Rules()
        for k, v in PRESETS[chosen].items():
            setattr(r, k, v)
        rows = "".join(
            f"<div class='zl-row'><span style='color:{UP};width:13px'>✓</span>"
            f"<span class='zl-muted' style='flex:1'>{t}</span></div>"
            for t in ["Only enters where price has turned before, never mid-range.",
                      "Waits for a candle to confirm the turn.",
                      f"Needs at least {r.min_rr}× more reward than risk.",
                      "Stops before big news announcements.",
                      "Sizes every trade so a loss stays within your limit."])
        panel("Always on", rows)

        if st.button("Start scanning", use_container_width=True):
            apply_preset(chosen)
            save_profile()
            st.session_state["stage"] = "app"
            st.rerun()


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def face_app():
    r: Rules = st.session_state["rules"]
    now = datetime.now(timezone.utc)
    events, cal_err = economic_calendar()
    upcoming = next_high_impact(events, now)
    tf_keys = list(TIMEFRAMES.keys())
    scan = st.session_state["scan"]
    beginner = st.session_state["beginner"]

    # ── header ──
    clocks = "".join(
        f"<div class='c'><div class='n'>{name}</div><div class='v'>"
        f"{(now + timedelta(hours=off)):%H:%M}</div></div>" for name, off in CLOCKS)
    live = [n for n, a, b in SESSIONS if a <= now.hour < b]
    scanned = st.session_state["scanned_at"]
    age = f"{int((now - scanned).total_seconds() // 60)}m ago" if scanned else "not yet"

    h1, h2, h3 = st.columns([2.5, 3, 1])
    with h1:
        st.markdown(f"""
        <div style='padding:2px 0'>
          <div style='display:flex;align-items:center;gap:8px'>
            <span style='width:17px;height:17px;border:1.5px solid {ACCENT};border-radius:5px;
                  position:relative;flex:none'>
              <span style='position:absolute;left:2.5px;right:2.5px;top:6.5px;height:1.5px;
                    background:{ACCENT};display:block'></span></span>
            <span style='letter-spacing:.2em;font-size:13px;font-weight:600'>ZONELOCK</span>
          </div>
          <div class='zl-muted' style='margin-top:2px;font-size:10.5px;letter-spacing:.05em'>
            SCAN · ANALYSE · RANK · RECORD</div>
        </div>""", unsafe_allow_html=True)
    with h2:
        st.markdown(f"<div class='zl-clock' style='padding-top:3px'>{clocks}</div>",
                    unsafe_allow_html=True)
    with h3:
        st.markdown(f"<div style='text-align:right;padding-top:2px'>"
                    f"<div style='font-size:12px'>{st.session_state['user'] or 'Trader'}</div>"
                    f"<div class='zl-muted' style='font-size:10px'>"
                    f"{st.session_state['preset']} · scan {age}</div></div>",
                    unsafe_allow_html=True)

    st.markdown(f"<div class='zl-pipe'>Scan <b>→</b> Setups <b>→</b> Analyse <b>→</b> "
                f"Levels <b>→</b> Rank <b>→</b> Alert <b>→</b> Journal"
                f"<span style='margin-left:auto;color:{ACCENT if live else FAINT}'>"
                f"{' + '.join(live) + ' OPEN' if live else 'MARKETS QUIET'}</span></div>",
                unsafe_allow_html=True)

    if st.session_state.get("tape", True):
        components.html(ticker_tape(st.session_state["watch"][:8]), height=50)

    with st.sidebar:
        st.markdown(f"<div style='letter-spacing:.22em;font-size:11px;color:{ACCENT}'>"
                    f"◈ ZONELOCK</div><div class='zl-muted'>{st.session_state['email']}</div>",
                    unsafe_allow_html=True)
        st.divider()
        st.session_state["watch"] = st.multiselect("Watchlist", list(SYMBOLS.keys()),
                                                   st.session_state["watch"])
        st.session_state["ladder"] = st.multiselect("Timeframes to read", tf_keys,
                                                    st.session_state["ladder"])
        st.session_state["account_size"] = st.number_input(
            "Account size ($)", 50.0, 1_000_000.0, st.session_state["account_size"], 50.0,
            key="sb_acct")
        st.session_state["beginner"] = st.toggle("Explain everything",
                                                 st.session_state["beginner"],
                                                 key="sb_beg")
        st.divider()
        if st.button("Save settings", use_container_width=True):
            st.success("Saved.") if save_profile() else st.warning("Could not save.")
        if st.button("Sign out", use_container_width=True, key="sb_out"):
            save_profile()
            st.session_state["stage"] = "login"
            st.rerun()

    if not st.session_state["ladder"]:
        st.session_state["ladder"] = ["M15", "H1", "H4", "D1"]

    tabs = st.tabs(["Dashboard", "Scanner", "A+ Setups", "Charts", "Analysis", "Levels",
                    "Risk", "News", "Journal", "Learn", "Settings"])

    def tf_picker(key: str):
        chosen = st.radio("Timeframe", tf_keys, index=tf_keys.index(st.session_state["tf"]),
                          horizontal=True, key=key, label_visibility="collapsed")
        if chosen != st.session_state["tf"]:
            st.session_state["tf"] = chosen
            st.rerun()

    def sym_picker(key: str):
        keys = list(SYMBOLS.keys())
        chosen = st.selectbox("Symbol", keys, index=keys.index(st.session_state["symbol"]),
                              key=key)
        if chosen != st.session_state["symbol"]:
            st.session_state["symbol"] = chosen
            st.rerun()
        return chosen

    # ── 1 · Dashboard ──
    def _dash():
        if not scan:
            note("Nothing scanned yet. Press the button and Zonelock reads every symbol on "
                 "your watchlist across every timeframe you chose.", "accent")
            if st.button("Scan the market now", use_container_width=True, key="d_scan0"):
                run_scan(r)
                st.rerun()
            if beginner:
                st.markdown("##### While you wait — what this app actually does")
                c1, c2 = st.columns(2)
                with c1:
                    explainer("The idea", viz.support_resistance(),
                              "Markets turn at the same prices over and over. Those prices "
                              "are the only places Zonelock will enter.")
                with c2:
                    explainer("The order it follows", viz.trade_lifecycle(),
                              "Five steps, every time, on every symbol. No guessing, no "
                              "chasing.")
            return

        rows = scan["rows"]
        found = [x for x in rows if x["decision"].taken]
        watching = [x for x in rows if x.get("watch")]
        a_grade = [x for x in found if x["grade"] == "A"]
        demo_n = len([x for x in rows if x["origin"] == "demo"])

        if demo_n:
            note(f"<b>{demo_n} of {len(rows)} symbols are on demo prices.</b> Crypto works "
                 f"free; gold, FX and indices need a free data key — <b>Settings → Market "
                 f"data</b>. Demo rows are marked.", "warn")

        st.markdown(f"""
        <div class='zl-stats'>
          <div class='zl-stat'><div class='k'>Scanned</div><div class='v mono'>{len(rows)}</div>
            <div class='s'>× {len(st.session_state['ladder'])} timeframes</div></div>
          <div class='zl-stat'><div class='k'>Ready to place</div>
            <div class='v mono' style='color:{UP if found else MUTED}'>{len(found)}</div>
            <div class='s'>confirmed setups</div></div>
          <div class='zl-stat'><div class='k'>Forming</div>
            <div class='v mono' style='color:{WARN if watching else MUTED}'>{len(watching)}</div>
            <div class='s'>at a level, not confirmed</div></div>
          <div class='zl-stat'><div class='k'>Best grade</div>
            <div class='v mono' style='color:{UP if a_grade else MUTED}'>
              {'A' if a_grade else (found[0]['grade'] if found else '—')}</div>
            <div class='s'>{len(a_grade)} A-grade</div></div>
        </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        if c1.button("Re-scan", use_container_width=True, key="d_scan"):
            run_scan(r)
            st.rerun()
        if upcoming:
            mins = int((upcoming["time"] - now).total_seconds() // 60)
            hh, mm = divmod(mins, 60)
            c2.markdown(f"<div class='zl-muted' style='padding-top:8px'>Next big news · "
                        f"<b>{upcoming['currency']} {upcoming['title']}</b> in "
                        f"{hh}h {mm:02d}m</div>", unsafe_allow_html=True)

        left, right = st.columns([1.45, 1])

        with left:
            trs = ""
            for row in rows:
                sym = row["symbol"]
                dig = SYMBOLS[sym]["digits"]
                cc = UP if row["change"] >= 0 else DOWN
                v = row["view"]
                bc = {"bullish": UP, "bearish": DOWN}.get(v.alignment, WARN)
                state, scol = state_of(row)
                trs += (f"<tr><td style='font-weight:500'>{SYMBOLS[sym]['mt5']}</td>"
                        f"<td class='num'>{row['price']:,.{dig}f}</td>"
                        f"<td class='num' style='color:{cc}'>{row['change']:+.2f}%</td>"
                        f"<td style='color:{bc}'>{v.alignment}</td>"
                        f"<td class='num'>{int(v.agreement*100)}%</td>"
                        f"<td><span style='color:{scol};font-size:10px;letter-spacing:.05em'>"
                        f"{state}</span></td></tr>")
            panel("Market overview",
                  f"<table class='zt'><tr><th>Symbol</th><th>Price</th><th>Today</th>"
                  f"<th>Bias</th><th>Agree</th><th>State</th></tr>{trs}</table>",
                  "LIVE" if any(x["origin"] != "demo" for x in rows) else "DEMO", flush=True)

            best = found[0] if found else (watching[0] if watching else rows[0])
            st.markdown(f"<div class='zp'><div class='zp-head'><span class='t'>"
                        f"{SYMBOLS[best['symbol']]['mt5']} · {best['tf']}</span>"
                        f"<span class='r'>{origin_chip(best['origin'])}</span></div></div>",
                        unsafe_allow_html=True)
            st.plotly_chart(chart(best, r, 110, True, 330), use_container_width=True,
                            config={"displayModeBar": False})

        with right:
            if found:
                trs = "".join(
                    f"<tr><td style='font-weight:500'>{SYMBOLS[x['symbol']]['mt5']}</td>"
                    f"<td>{x['tf']}</td>"
                    f"<td style='color:{UP if x['decision'].direction=='BUY' else DOWN}'>"
                    f"{x['decision'].direction}</td>"
                    f"<td class='num'>{x['decision'].rr}R</td>"
                    f"<td>{viz.confidence_bar(x['grade'])}</td></tr>" for x in found[:8])
                panel("Top setups",
                      f"<table class='zt'><tr><th>Symbol</th><th>TF</th><th>Side</th>"
                      f"<th>R:R</th><th>Confidence</th></tr>{trs}</table>",
                      f"{len(found)} found", flush=True)
            else:
                panel("Top setups",
                      "<div class='zl-muted'>Nothing confirmed right now. That is the "
                      "system working — it waits for proof, not hope.</div>")

            if watching:
                trs = "".join(
                    f"<tr><td style='font-weight:500'>{SYMBOLS[x['symbol']]['mt5']}</td>"
                    f"<td style='color:{UP if x['watch'].direction=='BUY' else DOWN}'>"
                    f"{x['watch'].direction}</td>"
                    f"<td class='num'>{pips(x['symbol'], x['watch'].distance):g}p</td>"
                    f"<td><span style='color:"
                    f"{UP if x['watch'].urgency=='imminent' else WARN};font-size:10px'>"
                    f"{x['watch'].urgency}</span></td></tr>" for x in watching[:6])
                panel("Forming — watch these",
                      f"<table class='zt'><tr><th>Symbol</th><th>Side</th><th>Away</th>"
                      f"<th>State</th></tr>{trs}</table>", flush=True)

            if events:
                trs = "".join(
                    f"<tr><td class='num'>{e['time']:%H:%M}</td><td>{e['currency']}</td>"
                    f"<td>{e['title'][:26]}</td><td>"
                    f"{viz.strength_bar({'high':100,'medium':60}.get(e['impact'],25), {'high':DOWN,'medium':WARN}.get(e['impact'],FAINT), 42)}"
                    f"</td></tr>" for e in [x for x in events if x['time'] > now][:6])
                panel("Economic calendar",
                      f"<table class='zt'><tr><th>Time</th><th>Cur</th><th>Event</th>"
                      f"<th>Impact</th></tr>{trs}</table>", "TODAY", flush=True)

    # ── 2 · Scanner ──
    def _scanner():
        st.markdown("<div class='zl-muted' style='margin-bottom:9px'><b>Step 1 — scan the "
                    "market.</b> Every symbol on your watchlist is read on every timeframe "
                    "you selected, then measured against your rules.</div>",
                    unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2.2])
        with c1:
            if st.button("Run scan", use_container_width=True, key="sc_run"):
                run_scan(r)
                st.rerun()
        with c2:
            tf_picker("tf_scan")

        if not scan:
            note("Press <b>Run scan</b> to begin.", "accent")
            return

        rows = scan["rows"]
        trs = ""
        for row in rows:
            sym = row["symbol"]
            dig = SYMBOLS[sym]["digits"]
            d = row["decision"]
            state, scol = state_of(row)
            sup = f"{row['support'].mid:,.{dig}f}" if row.get("support") else "—"
            res = f"{row['resistance'].mid:,.{dig}f}" if row.get("resistance") else "—"
            reason = d.verdict if not d.taken else f"{d.direction} · {d.rr}R"
            trs += (f"<tr><td style='font-weight:500'>{SYMBOLS[sym]['mt5']}</td>"
                    f"<td class='num'>{row['price']:,.{dig}f}</td>"
                    f"<td class='num' style='color:{UP}'>{sup}</td>"
                    f"<td class='num' style='color:{DOWN}'>{res}</td>"
                    f"<td class='num'>{pips(sym, row['atr']):g}p</td>"
                    f"<td>{viz.confidence_bar(row['grade'])}</td>"
                    f"<td><span style='color:{scol};font-size:10px'>{state}</span></td>"
                    f"<td class='zl-muted'>{reason}</td></tr>")
        panel("Scan result",
              f"<table class='zt'><tr><th>Symbol</th><th>Price</th><th>Support</th>"
              f"<th>Resistance</th><th>ATR</th><th>Grade</th><th>State</th>"
              f"<th>Verdict</th></tr>{trs}</table>",
              f"{len(rows)} symbols · {st.session_state['tf']}", flush=True)

        if scan["failed"]:
            with st.expander(f"{len(scan['failed'])} symbols could not be read"):
                for f in scan["failed"]:
                    st.markdown(f"<div class='zl-muted'>{f}</div>", unsafe_allow_html=True)

        if beginner:
            explainer("What the scanner is looking for", viz.zone_touches(),
                      "A level only counts once price has respected it more than once. "
                      "Your rules currently need "
                      f"<b>{r.min_zone_touches}</b> touches.")

    # ── 3 · Setups ──
    def _setups():
        st.markdown("<div class='zl-muted' style='margin-bottom:9px'><b>Step 2 — the "
                    "setups, ranked.</b> Each one is scored out of 100 from nine factors, "
                    "with news risk subtracted. 90+ is A+, 80+ is A, 70+ is B. Below 60 is "
                    "not shown.</div>", unsafe_allow_html=True)
        if not scan:
            note("Run a scan first.", "accent")
            return
        st.session_state["min_score"] = st.slider(
            "Only show setups scoring at least", 50, 95,
            st.session_state["min_score"], 5, key="su_floor")
        floor = st.session_state["min_score"]
        found = [x for x in scan["rows"] if x["decision"].taken
                 and x["score"] and x["score"].total >= floor]
        below = [x for x in scan["rows"] if x["decision"].taken
                 and x["score"] and x["score"].total < floor]
        watching = [x for x in scan["rows"] if x.get("watch")]

        if not found:
            note(f"Nothing scoring {floor} or above. Price has to be <i>at</i> a level "
                 f"<b>and</b> a candle has to close proving the turn — then the other "
                 f"factors have to add up.", "muted")
        for i, row in enumerate(found, 1):
            plan_card(row, "su_", i)

        if watching:
            st.markdown("##### Forming — not confirmed yet")
            for row in sorted(watching, key=lambda x: {"imminent": 0, "watching": 1,
                                                       "approaching": 2}[x["watch"].urgency]):
                watch_card(row["watch"], row["symbol"])

        if below:
            with st.expander(f"{len(below)} setups scored below {floor}"):
                for x in below:
                    sc = x["score"]
                    miss = ", ".join(f.name.lower() for f in sc.missing_factors[:3])
                    st.markdown(f"<div class='zl-row'>"
                                f"<span class='zl-chip' style='background:{sc.color}22;"
                                f"color:{sc.color}'>{sc.total}%</span>"
                                f"<span style='flex:1;font-size:12px'>"
                                f"{SYMBOLS[x['symbol']]['mt5']} · "
                                f"{x['plan'].setup_type if x.get('plan') else ''}</span>"
                                f"<span class='zl-muted' style='font-size:10.5px'>"
                                f"missing {miss}</span></div>",
                                unsafe_allow_html=True)

        passed = [x for x in scan["rows"] if not x["decision"].taken and not x.get("watch")]
        if passed:
            with st.expander(f"Why {len(passed)} symbols were passed over"):
                for row in passed:
                    st.markdown(f"<div class='zl-row'>"
                                f"<span class='zl-chip'>{SYMBOLS[row['symbol']]['mt5']}</span>"
                                f"<span style='flex:1;font-size:12px'>"
                                f"{row['decision'].headline}</span>"
                                f"<span style='color:{DOWN};font-size:10.5px'>"
                                f"{row['decision'].verdict}</span></div>",
                                unsafe_allow_html=True)

        if beginner:
            explainer("What makes a setup high-probability", viz.reversal_candles(),
                      "The engine will not act on price simply arriving at a level. One of "
                      "these shapes has to close there first — that is the difference "
                      "between a guess and a signal.")

    # ── 4 · Charts ──
    def _charts():
        quick = st.session_state["watch"][:6] or list(SYMBOLS.keys())[:6]
        picked = st.radio("Symbol", quick,
                          index=quick.index(st.session_state["symbol"])
                          if st.session_state["symbol"] in quick else 0,
                          horizontal=True, label_visibility="collapsed", key="ch_quick")
        if picked != st.session_state["symbol"]:
            st.session_state["symbol"] = picked
            st.rerun()
        tf_picker("tf_chart")

        sym = st.session_state["symbol"]
        row = cached_row(sym, r)
        price_header(row)

        c1, c2, c3 = st.columns([1.6, 1, 1])
        span = c1.radio("Bars", [60, 120, 200, 300], index=1, horizontal=True,
                        label_visibility="collapsed", key="ch_bars")
        show_daily = c2.toggle("Daily levels", True, key="ch_daily")
        engine = c3.radio("Engine", ["Zonelock", "TradingView"],
                          index=0 if st.session_state["engine"] == "Zonelock" else 1,
                          horizontal=True, label_visibility="collapsed", key="ch_eng")
        st.session_state["engine"] = engine

        if engine == "TradingView":
            d, dg = row["decision"], SYMBOLS[sym]["digits"]
            levels = []
            if d.taken:
                levels = [(f"{d.entry:,.{dg}f}", "Entry", INFO),
                          (f"{d.stop_loss:,.{dg}f}", "Stop loss", DOWN),
                          (f"{d.take_profit:,.{dg}f}", "Take profit", UP)]
            if row.get("support"):
                levels.append((f"{row['support'].mid:,.{dg}f}", "Support", UP))
            if row.get("resistance"):
                levels.append((f"{row['resistance'].mid:,.{dg}f}", "Resistance", DOWN))
            components.html(advanced_chart(sym, row["tf"], 540, levels=levels), height=560)
            st.caption(f"Live TradingView chart. Zonelock's levels are listed underneath — "
                       f"draw them with the horizontal-line tool, or switch back to the "
                       f"Zonelock chart to see them plotted for you.")
        else:
            st.plotly_chart(chart(row, r, span, show_daily), use_container_width=True,
                            config={"displayModeBar": False, "scrollZoom": True})
            legend = "".join(f"<span class='zl-chip'><span style='color:{c}'>—</span> {t}</span>"
                             for c, t in [(INFO, "Entry"), (DOWN, "Stop / resistance"),
                                          (UP, "Target / support"), (WARN, "Order block"),
                                          (A300, "Fair value gap"), (FAINT, "Daily levels")])
            st.markdown(f"<div>{legend}</div>", unsafe_allow_html=True)

        if row["decision"].taken:
            why_block(row)
        elif row.get("watch"):
            watch_card(row["watch"], sym)

    # ── 5 · Analysis ──
    def _analysis():
        st.markdown("<div class='zl-muted' style='margin-bottom:9px'><b>Step 3 — check "
                    "every timeframe agrees.</b> A setup on the 15-minute chart means little "
                    "if the daily chart is pointing the other way.</div>",
                    unsafe_allow_html=True)
        sym = sym_picker("an_sym")
        row = cached_row(sym, r)
        mtf_panel(row)

        dig = SYMBOLS[sym]["digits"]
        trs = ""
        for tf in ["M5", "M15", "M30", "H1", "H4", "D1", "W1"]:
            rd = row["view"].reads.get(tf)
            if not rd:
                continue
            c = {"bullish": UP, "bearish": DOWN}.get(rd.bias, WARN)
            trs += (f"<tr><td style='font-weight:500'>{tf}</td>"
                    f"<td class='zl-muted'>{TIMEFRAMES[tf]['label']}</td>"
                    f"<td style='color:{c}'>{rd.bias}</td>"
                    f"<td>{rd.structure if rd.structure != 'none' else '—'}</td>"
                    f"<td>{rd.at_zone}</td>"
                    f"<td class='num' style='color:{UP}'>"
                    f"{f'{rd.nearest_support:,.{dig}f}' if rd.nearest_support else '—'}</td>"
                    f"<td class='num' style='color:{DOWN}'>"
                    f"{f'{rd.nearest_resistance:,.{dig}f}' if rd.nearest_resistance else '—'}</td>"
                    f"<td class='zl-muted'>{rd.reversal or '—'}</td></tr>")
        panel("Every timeframe",
              f"<table class='zt'><tr><th>TF</th><th>Period</th><th>Bias</th>"
              f"<th>Structure</th><th>Price is</th><th>Support</th><th>Resistance</th>"
              f"<th>Candle</th></tr>{trs}</table>", flush=True)

        if beginner:
            c1, c2 = st.columns(2)
            with c1:
                explainer("Break of structure vs change of character", viz.bos_choch(),
                          "BOS means the trend is continuing. CHoCH means it has flipped. "
                          "Both create order blocks, but they mean opposite things.")
            with c2:
                explainer("Fair value gap", viz.fair_value_gap(),
                          "When price moves so fast it skips a range, it tends to come back "
                          "and fill it. An unfilled gap is unfinished business.")

    # ── 6 · Levels ──
    def _levels():
        st.markdown("<div class='zl-muted' style='margin-bottom:9px'><b>Step 4 — the map.</b> "
                    "These are the prices that matter today, worked out from yesterday's "
                    "daily candle and this week's range.</div>", unsafe_allow_html=True)
        sym = sym_picker("lv_sym")
        row = cached_row(sym, r)
        dig, price = SYMBOLS[sym]["digits"], row["price"]

        if beginner:
            explainer("What daily zones are and why they matter", viz.daily_zones(),
                      "Yesterday's high, low and close are watched by everyone trading this "
                      "market, so price reacts to them. Zonelock projects them forward as "
                      "today's map, then looks for its own setups near them — a setup sitting "
                      "on one of these is far stronger than one floating in open space.")

        if not row["levels"]:
            note("Daily candles are not available for this symbol right now.", "warn")
        else:
            trs = ""
            for lv in row["levels"]:
                col = {"resistance": DOWN, "support": UP}.get(lv.kind, FAINT)
                dist = pips(sym, lv.distance(price))
                trs += (f"<tr><td><span class='zl-chip' style='background:{col}22;"
                        f"color:{col}'>{lv.kind[:3].upper()}</span></td>"
                        f"<td style='font-weight:500'>{lv.name}</td>"
                        f"<td class='num'>{lv.price:,.{dig}f}</td>"
                        f"<td class='num zl-muted'>{dist:g} pips "
                        f"{'above' if lv.price > price else 'below'}</td></tr>")
            panel(f"{SYMBOLS[sym]['mt5']} · today's map",
                  f"<table class='zt'><tr><th>Type</th><th>Level</th><th>Price</th>"
                  f"<th>Distance</th></tr>{trs}</table>",
                  f"price {price:,.{dig}f}", flush=True)

        sup, res = row.get("support"), row.get("resistance")
        if sup or res:
            bits = []
            if res:
                bits.append(f"<div><div class='k'>Ceiling above</div>"
                            f"<div class='v mono' style='color:{DOWN}'>"
                            f"{res.mid:,.{dig}f}</div></div>")
            if sup:
                bits.append(f"<div><div class='k'>Floor below</div>"
                            f"<div class='v mono' style='color:{UP}'>"
                            f"{sup.mid:,.{dig}f}</div></div>")
            if sup and res:
                bits.append(f"<div><div class='k'>Room between</div>"
                            f"<div class='v mono'>{pips(sym, res.mid - sup.mid):g} pips</div></div>")
                pos = (price - sup.mid) / max(res.mid - sup.mid, 1e-9) * 100
                bits.append(f"<div><div class='k'>Price sits at</div>"
                            f"<div class='v mono'>{pos:.0f}% of range</div></div>")
            panel("The two levels Zonelock is trading between",
                  f"<div class='zl-lv' style='margin:0;padding:0;border:none'>"
                  f"{''.join(bits)}</div>")

    # ── 7 · Risk ──
    def _risk():
        st.markdown("<div class='zl-muted' style='margin-bottom:9px'><b>Step 5 — size it.</b> "
                    "The stop distance decides the lot size. Never the other way round.</div>",
                    unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            sym = st.selectbox("Symbol", list(SYMBOLS.keys()),
                               index=list(SYMBOLS.keys()).index(st.session_state["symbol"]),
                               key="rk_sym")
            bal = st.number_input("Account balance ($)", 10.0, 1_000_000.0,
                                  st.session_state["account_size"], 10.0, key="rk_bal")
            risk_pct = st.slider("Risk per trade (%)", 0.25, 5.0, r.risk_percent, 0.25,
                                 key="rk_pct")
            row = cached_row(sym, r)
            dig = SYMBOLS[sym]["digits"]
            d = row["decision"]
            default_entry = float(d.entry) if d.taken else row["price"]
            default_stop = float(d.stop_loss) if d.taken else (
                row["support"].low if row.get("support") else row["price"] * 0.995)
            entry = st.number_input("Entry price", value=round(default_entry, dig),
                                    format=f"%.{dig}f", step=float(SYMBOLS[sym]["pip"]),
                                    key="rk_entry")
            stop = st.number_input("Stop loss price", value=round(default_stop, dig),
                                   format=f"%.{dig}f", step=float(SYMBOLS[sym]["pip"]),
                                   key="rk_stop")
            target = st.number_input(
                "Take profit price",
                value=round(float(d.take_profit) if d.taken
                            else (row["resistance"].mid if row.get("resistance")
                                  else row["price"] * 1.01), dig),
                format=f"%.{dig}f", step=float(SYMBOLS[sym]["pip"]), key="rk_tp")

        with c2:
            risk_dist = abs(entry - stop)
            rew_dist = abs(target - entry)
            rp, wp = pips(sym, risk_dist), pips(sym, rew_dist)
            rr = round(rew_dist / risk_dist, 2) if risk_dist else 0.0
            lots = calculate_lot_size(bal, risk_pct, entry, stop, 1.0,
                                      SYMBOLS[sym]["pip"], r)
            cash_risk = bal * risk_pct / 100
            rr_col = UP if rr >= r.min_rr else DOWN

            st.markdown(f"""
            <div class='zp'><div class='zp-head'><span class='t'>Position size</span>
              <span class='r'>{SYMBOLS[sym]['mt5']}</span></div>
              <div class='zp-body'>
                <div style='display:flex;align-items:baseline;gap:10px'>
                  <span class='mono' style='font-size:32px;font-weight:500'>{lots:.2f}</span>
                  <span class='zl-muted'>lots</span>
                  <span style='margin-left:auto;font-size:19px;color:{rr_col}'
                        class='mono'>{rr:g}R</span>
                </div>
                <div class='zl-lv'>
                  <div><div class='k'>Risking</div><div class='v mono' style='color:{DOWN}'>
                    ${cash_risk:,.2f}</div></div>
                  <div><div class='k'>To make</div><div class='v mono' style='color:{UP}'>
                    ${cash_risk * rr:,.2f}</div></div>
                  <div><div class='k'>Stop</div><div class='v mono'>{rp:g} pips</div></div>
                  <div><div class='k'>Target</div><div class='v mono'>{wp:g} pips</div></div>
                </div>
              </div></div>""", unsafe_allow_html=True)

            if rr < r.min_rr:
                note(f"This trade only pays {rr:g}× what it risks. Your rules require "
                     f"{r.min_rr}×, so Zonelock would skip it.", "down")
            else:
                note(f"Reward is {rr:g}× the risk — this clears your {r.min_rr}× minimum.", "up")

            st.markdown(viz.risk_reward(max(rr, 0.3)), unsafe_allow_html=True)

        st.markdown("##### Your limits")
        wins_needed = int(1 / (1 + max(rr, 0.01)) * 100) + 1 if rr else 100
        panel("What this means over many trades",
              f"<div class='zl-lv' style='margin:0;padding:0;border:none'>"
              f"<div><div class='k'>Break-even win rate</div><div class='v mono'>"
              f"{wins_needed}%</div></div>"
              f"<div><div class='k'>Max open trades</div><div class='v mono'>"
              f"{r.max_open_positions}</div></div>"
              f"<div><div class='k'>Daily loss limit</div><div class='v mono' "
              f"style='color:{DOWN}'>${r.max_daily_loss:,.0f}</div></div>"
              f"<div><div class='k'>Daily profit cap</div><div class='v mono' "
              f"style='color:{UP}'>${r.daily_profit_cap:,.0f}</div></div></div>"
              f"<div class='zl-muted' style='margin-top:9px'>At {rr:g}R you only need to be "
              f"right {wins_needed}% of the time to break even. That is why the reward "
              f"filter matters more than being right.</div>")

        if beginner:
            explainer("How the size is worked out", viz.lot_size(),
                      "You choose the percentage. The distance to your stop does the rest. "
                      "A wider stop means fewer lots, so the money at risk stays the same.")

    # ── 8 · News ──
    def _news():
        t1, t2 = st.tabs(["Calendar", "Headlines"])
        with t1:
            if cal_err:
                note(f"Live calendar could not load — {cal_err}.", "warn")
            ahead = [e for e in events if e["time"] > now][:16]
            st.markdown(f"<div class='zl-muted' style='margin-bottom:8px'>Zonelock stops "
                        f"taking new trades {r.news_block_minutes} minutes either side of a "
                        f"high-impact release — those are the moments price moves for "
                        f"reasons no chart can see.</div>", unsafe_allow_html=True)
            if not ahead:
                note("Nothing further scheduled this week.", "muted")
            trs = ""
            for e in ahead:
                mins = int((e["time"] - now).total_seconds() // 60)
                when = f"in {mins}m" if mins < 90 else f"{e['time']:%a %H:%M}"
                col = {"high": DOWN, "medium": WARN}.get(e["impact"], FAINT)
                blocked = e["impact"] == "high" and mins <= r.news_block_minutes
                trs += (f"<tr><td class='num'>{when}</td><td>{e['currency']}</td>"
                        f"<td>{e['title']}</td>"
                        f"<td>{viz.strength_bar({'high':100,'medium':60}.get(e['impact'],25), col, 46)}</td>"
                        f"<td class='num zl-muted'>{e['forecast']}</td>"
                        f"<td class='num zl-muted'>{e['previous']}</td>"
                        f"<td>{'<span style=color:'+DOWN+';font-size:10px>PAUSED</span>' if blocked else ''}</td>"
                        f"</tr>")
            panel("This week", f"<table class='zt'><tr><th>When</th><th>Cur</th>"
                  f"<th>Event</th><th>Impact</th><th>Forecast</th><th>Previous</th>"
                  f"<th></th></tr>{trs}</table>", flush=True)
        with t2:
            items, err = headlines()
            if err:
                note(err, "warn")
            for h in items:
                st.markdown(f"<div class='zp'><div class='zp-body'>"
                            f"<div style='font-size:13px;line-height:1.45'>"
                            f"<a href='{h['link']}' target='_blank'>{h['title']}</a></div>"
                            f"<div class='zl-muted' style='margin-top:3px'>{h['source']} · "
                            f"{h['when']}</div></div></div>", unsafe_allow_html=True)

    # ── 9 · Journal ──
    def _journal():
        st.markdown("<div class='zl-muted' style='margin-bottom:9px'><b>Step 7 — record the "
                    "result.</b> Every pick you logged, with the reasoning it was based on. "
                    "This is how you find out whether the rules work.</div>",
                    unsafe_allow_html=True)
        rows = picks()
        t1, t2, t3 = st.tabs(["Picks", "Performance", "Notes"])

        with t1:
            if not rows:
                note("Nothing logged yet. Press <b>Log pick</b> on any setup.", "muted")
            else:
                st.dataframe(pd.DataFrame([{
                    "When": x["at"][5:16].replace("T", " "), "Symbol": x["mt5"],
                    "TF": x.get("tf", ""), "Grade": x["grade"], "Side": x["direction"],
                    "Entry": x["entry"], "SL": x["sl"], "TP": x["tp"],
                    "Risk pips": x.get("risk_pips"), "Reward pips": x.get("reward_pips"),
                    "R:R": x["rr"], "Lots": x["lots"], "Result": x.get("outcome", "")}
                    for x in rows]), use_container_width=True, hide_index=True)
                st.markdown("##### The reasoning behind each")
                for x in rows[:20]:
                    with st.expander(f"{x['mt5']} {x['direction']} · {x['grade']}-grade · "
                                     f"{x.get('tf','')} · {x['at'][5:16]}"):
                        st.write(x["headline"])
                        if x.get("why"):
                            st.markdown("".join(
                                f"<div class='zl-why'><span class='n'>{i}</span>"
                                f"<span style='flex:1;font-size:12px;line-height:1.5'>{w}"
                                f"</span></div>" for i, w in enumerate(x["why"], 1)),
                                unsafe_allow_html=True)

        with t2:
            if not rows:
                note("Log a few picks and the numbers appear here.", "muted")
            else:
                by_grade = {g: [x for x in rows if x["grade"] == g] for g in "ABC"}
                cells = "".join(
                    f"<div><div class='k'>{g}-grade</div><div class='v mono' "
                    f"style='color:{GRADE[g]}'>{len(v)}</div></div>"
                    for g, v in by_grade.items() if v)
                panel("What you have been picking",
                      f"<div class='zl-lv' style='margin:0;padding:0;border:none'>{cells}"
                      f"<div><div class='k'>Avg R:R</div><div class='v mono'>"
                      f"{sum(x.get('rr') or 0 for x in rows)/max(len(rows),1):.2f}</div></div>"
                      f"</div>")
                st.markdown("##### Prove the rules on history")
                st.markdown("<div class='zl-muted' style='margin-bottom:8px'>Replays your "
                            "exact rules bar by bar over past data, with no peeking ahead. "
                            "A bar that hits both stop and target counts as a loss, so the "
                            "result leans against you on purpose.</div>",
                            unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1.2, 1, 1])
                bt_sym = c1.selectbox("Symbol", list(SYMBOLS.keys()), key="bt_sym")
                bt_tf = c2.selectbox("Timeframe", tf_keys,
                                     index=tf_keys.index(st.session_state["tf"]), key="bt_tf")
                depth = c3.select_slider("History", [400, 700, 1000], value=700, key="bt_d")
                g1, g2 = st.columns(2)
                do_run = g1.button("Run backtest", use_container_width=True)
                do_sweep = g2.button("Which settings work best?", use_container_width=True)
                if do_run or do_sweep:
                    try:
                        df, origin = fetch(bt_sym, bt_tf, depth, st.session_state["td_key"])
                    except Exception as exc:
                        st.error(f"Could not load history: {exc}")
                        return
                    if origin == "demo":
                        note("<b>Demo data</b> — this proves the rules run, not that they "
                             "make money. Add a data key in Settings.", "warn")
                    tick = SYMBOLS[bt_sym]["pip"]
                    if do_sweep:
                        for param, values, label in [
                                ("min_rr", [1.2, 1.5, 2.0, 2.5, 3.0], "Minimum reward"),
                                ("min_zone_touches", [1, 2, 3, 4], "Zone touches")]:
                            with st.spinner(f"Testing {label.lower()}…"):
                                out = backtest_sweep(bt_sym, df, r, param, values,
                                                     balance=bal_of(), tick_size=tick)
                            best = max(out, key=lambda x: x["expectancy"])
                            st.markdown(f"**{label}**")
                            st.dataframe(pd.DataFrame([{
                                label: x["value"], "Trades": x["trades"],
                                "Win %": x["win_rate"], "Total R": x["total_r"],
                                "Expectancy": x["expectancy"], "PF": x["profit_factor"]}
                                for x in out]), use_container_width=True, hide_index=True)
                            st.markdown(f"<div class='zl-muted' style='margin:-4px 0 12px'>"
                                        f"Best here: <b>{best['value']}</b> · expectancy "
                                        f"{best['expectancy']:+.2f}R. Yours is "
                                        f"{getattr(r, param)}.</div>",
                                        unsafe_allow_html=True)
                        return
                    with st.spinner(f"Replaying {len(df)} bars…"):
                        res = backtest_run(bt_sym, df, r, balance=bal_of(), tick_size=tick)
                    if not res.closed:
                        note("No trades triggered. Your rules are very strict here — try "
                             "the settings test, or loosen one rule.", "warn")
                        return
                    pfc = UP if res.profit_factor >= 1.2 else (
                        WARN if res.profit_factor >= 1.0 else DOWN)
                    st.markdown(f"""
                    <div class='zl-stats'>
                      <div class='zl-stat'><div class='k'>Trades</div>
                        <div class='v mono'>{len(res.closed)}</div>
                        <div class='s'>over {res.bars} bars</div></div>
                      <div class='zl-stat'><div class='k'>Win rate</div>
                        <div class='v mono'>{res.win_rate:.0f}%</div>
                        <div class='s'>{len(res.wins)}W · {len(res.losses)}L</div></div>
                      <div class='zl-stat'><div class='k'>Profit factor</div>
                        <div class='v mono' style='color:{pfc}'>{res.profit_factor}</div>
                        <div class='s'>1.2+ is workable</div></div>
                      <div class='zl-stat'><div class='k'>Per trade</div>
                        <div class='v mono' style='color:{UP if res.expectancy>0 else DOWN}'>
                          {res.expectancy:+.2f}R</div>
                        <div class='s'>expectancy</div></div>
                    </div>""", unsafe_allow_html=True)
                    vc = UP if res.total_r > 0 else DOWN
                    panel("Verdict",
                          f"<div style='font-size:15px;color:{vc}'>{res.verdict}</div>"
                          f"<div class='zl-lv'>"
                          f"<div><div class='k'>Total</div><div class='v mono' "
                          f"style='color:{vc}'>{res.total_r:+.1f}R</div></div>"
                          f"<div><div class='k'>Worst fall</div><div class='v mono' "
                          f"style='color:{DOWN}'>{res.max_drawdown:.1f}R</div></div>"
                          f"<div><div class='k'>Losing streak</div><div class='v mono'>"
                          f"{res.longest_losing_streak}</div></div>"
                          f"<div><div class='k'>In money</div><div class='v mono'>"
                          f"${res.total_r * bal_of() * r.risk_percent / 100:,.0f}</div></div>"
                          f"</div>")
                    eq = go.Figure(go.Scatter(y=res.equity, mode="lines",
                                              line=dict(color=ACCENT, width=1.8),
                                              fill="tozeroy",
                                              fillcolor="rgba(145,132,217,.14)",
                                              showlegend=False))
                    eq.update_layout(height=190, margin=dict(l=4, r=8, t=4, b=4),
                                     paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                                     font=dict(color=MUTED, size=10,
                                               family="JetBrains Mono, monospace"),
                                     xaxis=dict(gridcolor="rgba(233,233,237,.05)",
                                                zeroline=False),
                                     yaxis=dict(gridcolor="rgba(233,233,237,.06)",
                                                zeroline=True,
                                                zerolinecolor="rgba(233,233,237,.18)"))
                    st.plotly_chart(eq, use_container_width=True,
                                    config={"displayModeBar": False})

        with t3:
            st.session_state["notes"] = st.text_area(
                "Your trading notes", st.session_state["notes"], height=160,
                placeholder="What you noticed today, mistakes to avoid, what to watch "
                            "tomorrow…")
            checks = ["Checked the higher timeframe agreed",
                      "Waited for the candle to close",
                      "Kept risk at or under my limit",
                      "Set the stop before the target",
                      "Reviewed the trade after it closed"]
            for i, c in enumerate(checks):
                st.checkbox(c, key=f"chk{i}")
            if st.button("Save notes", use_container_width=True):
                st.success("Saved.") if save_profile() else st.warning("Could not save.")

    def bal_of():
        return st.session_state["account_size"]

    # ── 10 · Learn ──
    def _learn():
        st.markdown("<div class='zl-muted' style='margin-bottom:10px'>Everything Zonelock "
                    "looks at, drawn. You do not need to know any of this for the app to "
                    "work — but it is a lot easier to trust a signal you understand.</div>",
                    unsafe_allow_html=True)

        t1, t2, t3 = st.tabs(["The basics", "What it looks for", "Managing risk"])
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                explainer("Support and resistance", viz.support_resistance(),
                          "<b>Support</b> is a price where buyers have stepped in before — a "
                          "floor. <b>Resistance</b> is where sellers have — a ceiling. "
                          "Zonelock only ever enters at one of these two places, because "
                          "everywhere else is a coin flip.")
                explainer("Why a level needs several touches", viz.zone_touches(),
                          "The first bounce could be luck. By the third, enough traders are "
                          "watching that price reacts again. Your rules need "
                          f"<b>{r.min_zone_touches}</b>.")
            with c2:
                explainer("The whole process", viz.trade_lifecycle(),
                          "Five steps, identical every time. The discipline is the edge — "
                          "not cleverness.")
                explainer("Market sessions", viz.session_clock(),
                          "The same symbol behaves differently at different hours. Zonelock "
                          "skips a market outside its liquid session, because thin markets "
                          "make false moves.")
        with t2:
            c1, c2 = st.columns(2)
            with c1:
                explainer("Reversal candles", viz.reversal_candles(),
                          "The proof that a level is holding. Price arriving is not enough — "
                          "one of these shapes has to <b>close</b> there. This single rule is "
                          "what separates the app from guessing.")
                explainer("Fair value gap", viz.fair_value_gap(),
                          "A gap left by a move so fast that nobody traded inside it. Price "
                          "usually returns to fill it, which makes an unfilled gap a magnet "
                          "and a clue about direction.")
            with c2:
                explainer("Order blocks", viz.order_block(),
                          "The last candle against the move, right before a big breakout — "
                          "where large orders were sitting. When price comes back to it, "
                          "those buyers are often still there.")
                explainer("BOS and CHoCH", viz.bos_choch(),
                          "<b>Break of structure</b> — the trend pushes past its last high, "
                          "so it continues. <b>Change of character</b> — it breaks a low "
                          "instead, so the trend has turned. Zonelock only trusts an order "
                          "block created by one of these.")
        with t3:
            c1, c2 = st.columns(2)
            with c1:
                explainer("Risk and reward", viz.risk_reward(r.min_rr),
                          f"Your stop is what you lose if wrong. Your target is what you "
                          f"make if right. Zonelock will not take a trade unless the target "
                          f"is at least <b>{r.min_rr}×</b> the stop — which means you can be "
                          f"wrong more often than right and still finish ahead.")
            with c2:
                explainer("Position size", viz.lot_size(),
                          "You never pick the lot size. You pick a percentage of your "
                          "account, and the distance to your stop decides the rest. Wider "
                          "stop, smaller size — the money at risk never changes.")
            explainer("Daily zones", viz.daily_zones(),
                      "Yesterday's high, low and close are on every serious trader's chart, "
                      "so price reacts to them. Zonelock projects them onto today and gives "
                      "extra weight to setups that land on one.")

    # ── 11 · Settings ──
    def _settings():
        t1, t2, t3, t4 = st.tabs(["Account", "Rules", "Data & alerts", "Install"])

        with t1:
            st.markdown(f"""
            <div class='zp'><div class='zp-head'><span class='t'>Signed in</span></div>
              <div class='zp-body'>
                <div style='display:flex;align-items:center;gap:12px'>
                  <div style='width:38px;height:38px;border-radius:50%;background:{A800};
                       display:grid;place-items:center;color:{A300};font-size:15px'>
                    {(st.session_state['user'] or 'T')[0].upper()}</div>
                  <div style='flex:1'>
                    <div style='font-size:15px'>{st.session_state['user'] or 'Trader'}</div>
                    <div class='zl-muted'>{st.session_state['email']}</div></div>
                </div>
                <div class='zl-lv'>
                  <div><div class='k'>Style</div><div class='v' style='font-size:13px'>
                    {st.session_state['preset']}</div></div>
                  <div><div class='k'>Account</div><div class='v mono' style='font-size:13px'>
                    ${st.session_state['account_size']:,.0f}</div></div>
                  <div><div class='k'>Watchlist</div><div class='v' style='font-size:13px'>
                    {len(st.session_state['watch'])}</div></div>
                  <div><div class='k'>Picks logged</div><div class='v' style='font-size:13px'>
                    {len(picks())}</div></div>
                </div>
              </div></div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("Save everything", use_container_width=True, key="st_save"):
                st.success("Saved.") if save_profile() else st.warning("Could not save.")
            if c2.button("Sign out", use_container_width=True, key="st_out"):
                save_profile()
                st.session_state["stage"] = "login"
                st.rerun()
            st.session_state["beginner"] = st.toggle(
                "Show the explanations everywhere", st.session_state["beginner"],
                key="st_beg", help="Turn off once you know the terms.")
            st.session_state["tape"] = st.toggle("Show the price ticker",
                                                 st.session_state.get("tape", True),
                                                 key="st_tape")

        with t2:
            chosen = st.radio("Style", list(PRESETS.keys()),
                              index=list(PRESETS.keys()).index(st.session_state["preset"]),
                              horizontal=True,
                              captions=["1% · needs 2×", "2% · needs 1.5×", "3% · looser"])
            if chosen != st.session_state["preset"]:
                apply_preset(chosen)
                st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### When it will enter")
                r.require_reversal_candle = st.toggle(
                    "Wait for a reversal candle", r.require_reversal_candle,
                    help="Strongly recommended. Without it the app enters on price touching "
                         "a level, with no proof it is holding.", key="st_rev")
                r.require_fvg_unfilled = st.toggle("Need an unfilled gap",
                                                   r.require_fvg_unfilled, key="st_fvg")
                r.require_ob_structure = st.toggle("Order block must come from a break",
                                                   r.require_ob_structure, key="st_ob")
                r.accept_choch = st.toggle("Allow trend-reversal entries", r.accept_choch,
                                           key="st_choch")
                r.min_zone_touches = st.slider("Times price must have respected the level",
                                               1, 5, r.min_zone_touches,
                                               key="st_touch")
                r.zone_atr_mult = st.slider("How thick a level counts as", 0.1, 1.0,
                                            float(r.zone_atr_mult), 0.05,
                                            key="st_thick")
                r.swing_lookback = st.slider("How far back to look for turns", 2, 8,
                                             r.swing_lookback, key="st_swing")
            with c2:
                st.markdown("##### Money")
                r.base_lot = st.number_input("Smallest lot size", 0.01, 5.0, r.base_lot,
                                             0.01, format="%.2f", key="st_lot")
                r.risk_percent = st.slider("Risk per trade (%)", 0.25, 5.0,
                                           r.risk_percent, 0.25, key="st_risk")
                r.min_rr = st.slider("Reward must be at least this × the risk", 1.0, 4.0,
                                     r.min_rr, 0.1, key="st_rr")
                r.max_open_positions = st.slider("Most trades open at once", 1, 10,
                                                 r.max_open_positions, key="st_open")
                r.daily_profit_cap = st.number_input("Stop for the day after making ($)",
                                                     0.0, 5000.0, r.daily_profit_cap,
                                                     5.0, key="st_cap")
                r.max_daily_loss = st.number_input("Stop for the day after losing ($)",
                                                   0.0, 5000.0, r.max_daily_loss, 5.0,
                                                   key="st_loss")
                st.markdown("##### Timing")
                r.news_block_minutes = st.slider("Minutes to avoid around big news", 0, 120,
                                                 r.news_block_minutes, 5, key="st_news")
                r.session_filter = st.toggle("Only trade a market in its own hours",
                                             r.session_filter, key="st_sess")
            st.session_state["rules"] = r
            c1, c2 = st.columns(2)
            if c1.button("Save rules", use_container_width=True):
                st.success("Saved — they load next time you sign in.") if save_profile() \
                    else st.warning("Could not save.")
            if c2.button("Re-scan with these", use_container_width=True):
                run_scan(r)
                st.rerun()

        with t3:
            st.markdown("##### Market data")
            note("Crypto comes from <b>Binance</b> — free, no key, works everywhere. "
                 "Gold, FX, indices and oil need a key when the host is blocked, which it "
                 "usually is on free cloud hosting.<br><br>Free key at <b>twelvedata.com</b> "
                 "— 800 calls a day, no card.", "accent")
            st.session_state["td_key"] = st.text_input("Twelve Data API key",
                                                       st.session_state["td_key"],
                                                       type="password")
            if st.button("Test the key"):
                try:
                    df, origin = fetch("XAUUSD", "M15", 100, st.session_state["td_key"],
                                       allow_demo=False)
                    st.success(f"Working — gold via {origin}, "
                               f"last {float(df['close'].iloc[-1]):,.2f}")
                except Exception as exc:
                    st.warning(f"Still failing: {exc}")

            st.markdown("##### Phone alerts")
            note("1 · Message <b>@BotFather</b> on Telegram, send <code>/newbot</code>, copy "
                 "the token.<br>2 · Message your new bot once.<br>3 · Message "
                 "<b>@userinfobot</b> for your chat id.", "muted")
            st.session_state["tg_token"] = st.text_input("Bot token",
                                                         st.session_state["tg_token"],
                                                         type="password")
            st.session_state["tg_chat"] = st.text_input("Chat id",
                                                        st.session_state["tg_chat"])
            if st.button("Send a test message"):
                ok, msg = telegram("<b>Zonelock</b>\nAlerts are working.")
                st.success(msg) if ok else st.warning(msg)

            st.markdown("##### Scanning while the app is closed")
            st.markdown("<div class='zl-muted'>Run <code>scanner.py</code> on GitHub Actions "
                        "every 15 minutes — same rules, same Telegram chat, nothing open. "
                        "See SCANNER.md.</div>", unsafe_allow_html=True)

        with t4:
            note("<b>iPhone</b> — open in Safari → Share → Add to Home Screen.<br>"
                 "<b>Android</b> — Chrome → ⋮ → Install app.<br>"
                 "<b>Windows / tablet</b> — Edge → ⋯ → Apps → Install this site.<br><br>"
                 "It then opens full screen with no browser bar, like a normal app, and "
                 "remembers your settings.", "accent")
            st.markdown("<div class='zl-muted'>The layout already reflows for phones — "
                        "tables get tighter, panels stack, and the tab row scrolls "
                        "sideways.</div>", unsafe_allow_html=True)

    fns = [_dash, _scanner, _setups, _charts, _analysis, _levels, _risk, _news,
           _journal, _learn, _settings]
    labels = ["Dashboard", "Scanner", "A+ Setups", "Charts", "Analysis", "Levels", "Risk",
              "News", "Journal", "Learn", "Settings"]
    for tab, fn, label in zip(tabs, fns, labels):
        with tab:
            safe(fn, label)


{"login": face_login, "setup": face_setup, "app": face_app}[st.session_state["stage"]]()
