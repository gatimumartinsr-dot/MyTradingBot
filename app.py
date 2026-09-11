"""
app.py — Zonelock: multi-timeframe support & resistance scanner.

Reads free market data across M5→W1, applies your rules on each timeframe,
and hands you setups to place yourself on MT5. No broker, no credentials.

    pip install -r requirements.txt
    streamlit run app.py
"""

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market import (MTF_LADDER, SYMBOLS, TIMEFRAMES, DataError, cache_age,
                    fetch, pips, spread_note)
from strategy import (Rules, atr, build_zones, confluence, daily_zones,
                      evaluate, explain, find_fvgs, mtf_grade, multi_timeframe,
                      order_blocks, reversal_watch)

PICKS = os.environ.get("ZONELOCK_PICKS", "picks.jsonl")
PROFILE = os.environ.get("ZONELOCK_PROFILE", "profile.json")

BG, SURFACE, RAISED = "#161826", "#1e2030", "#252838"
TEXT, MUTED, FAINT = "#e9e9ed", "#9397ab", "#5f6376"
ACCENT, A300, A700, A800 = "#9184d9", "#d2cefd", "#5d5294", "#3a3360"
UP, DOWN, WARN = "#5fbf8f", "#e07b87", "#d9b26a"
LINE = "rgba(233,233,237,.10)"
GRADE = {"A": UP, "B": A300, "C": WARN, "—": FAINT}
ORIGIN_COLOR = {"binance": UP, "twelvedata": UP, "stooq": A300,
                "yahoo": A300, "cache": WARN, "demo": DOWN}

st.set_page_config(page_title="Zonelock", layout="wide", page_icon="◈",
                   initial_sidebar_state="collapsed")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
  html, body, [data-testid='stAppViewContainer'], [data-testid='stMain'] {{
      background:{BG} !important; color:{TEXT} !important;
      font-family:Inter, system-ui, sans-serif; -webkit-font-smoothing:antialiased; }}
  [data-testid='stHeader'], [data-testid='stToolbar'], [data-testid='stDecoration'],
  [data-testid='stStatusWidget'] {{ display:none !important; height:0 !important; }}
  [data-testid='stSidebar'] {{ background:{SURFACE} !important; border-right:1px solid {LINE}; }}
  .block-container {{ padding:0.85rem 1.4rem 4rem !important; max-width:1560px; }}
  #MainMenu, footer {{ visibility:hidden; }}
  ::selection {{ background:{A800}; color:{TEXT}; }}
  *:focus-visible {{ outline:2px solid {ACCENT} !important; outline-offset:2px !important; }}
  h1,h2,h3,h4,h5,h6 {{ font-weight:500 !important; letter-spacing:-.015em; color:{TEXT} !important; }}
  .mono {{ font-family:'JetBrains Mono', ui-monospace, monospace; font-variant-numeric:tabular-nums; }}

  .stTabs [data-baseweb='tab-list'] {{ position:sticky; top:0; z-index:99; gap:2px;
      background:{BG}; padding:6px 0 0; margin-bottom:14px; border-bottom:1px solid {LINE};
      overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none; }}
  .stTabs [data-baseweb='tab-list']::-webkit-scrollbar {{ display:none; }}
  .stTabs [data-baseweb='tab'] {{ background:transparent !important; color:{MUTED} !important;
      padding:9px 14px !important; font-size:13px !important; font-weight:500 !important;
      white-space:nowrap; border-radius:8px 8px 0 0; transition:color .15s ease; }}
  .stTabs [data-baseweb='tab']:hover {{ color:{A300} !important;
      background:rgba(145,132,217,.07) !important; }}
  .stTabs [aria-selected='true'] {{ color:{TEXT} !important; background:{SURFACE} !important;
      border-bottom:2px solid {ACCENT} !important; }}
  .stTabs [data-baseweb='tab-highlight'], .stTabs [data-baseweb='tab-border'] {{ display:none !important; }}

  .stButton>button, .stDownloadButton>button {{ background:transparent !important;
      border:1px solid {ACCENT} !important; color:{A300} !important; border-radius:8px !important;
      font-weight:500 !important; font-size:13.5px !important; padding:8px 16px !important;
      transition:background .15s ease !important; }}
  .stButton>button:hover, .stDownloadButton>button:hover {{
      background:rgba(145,132,217,.14) !important; color:{A300} !important; }}
  .stButton>button:active {{ background:rgba(145,132,217,.24) !important; }}
  .stButton>button:focus:not(:active) {{ border-color:{ACCENT} !important; color:{A300} !important; }}

  [data-baseweb='radio'] [aria-checked='true'] > div:first-child,
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
      border-radius:10px !important; }}
  a, a:visited {{ color:{A300} !important; text-decoration:none; }}
  a:hover {{ color:{ACCENT} !important; }}
  code {{ background:{RAISED} !important; color:{A300} !important; border-radius:6px; }}
  [data-testid='stDataFrame'] {{ border:1px solid {LINE}; border-radius:9px; overflow:hidden; }}

  .zl-strip {{ display:flex; align-items:center; gap:16px; flex-wrap:wrap;
      background:linear-gradient(135deg,{RAISED},{SURFACE} 62%); border:1px solid {LINE};
      border-radius:10px; padding:12px 16px; margin-bottom:12px; }}
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
      border-radius:5px; background:{RAISED}; color:{TEXT}; margin-right:5px;
      margin-bottom:3px; white-space:nowrap; }}
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
      line-height:1.9; }}
  .zl-tf {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
  .zl-tf-cell {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:9px; padding:11px 12px; }}
  .zl-tf-cell .tf {{ font-size:11px; letter-spacing:.1em; color:{FAINT}; }}
  .zl-tf-cell .bias {{ font-size:15px; font-weight:500; margin-top:3px; }}
  .zl-bar {{ height:5px; border-radius:3px; background:{RAISED}; overflow:hidden; margin-top:8px; }}
  .zl-why {{ display:flex; gap:9px; align-items:flex-start; padding:7px 0; }}
  .zl-why .n {{ width:18px; height:18px; border-radius:5px; background:{A800}; color:{A300};
      font-size:10px; display:inline-flex; align-items:center; justify-content:center; flex:none;
      margin-top:1px; }}
  .zl-mkt {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(168px,1fr)); gap:8px; }}
  .zl-mkt-cell {{ background:{SURFACE}; border:1px solid {LINE}; border-radius:9px; padding:11px 12px; }}

  @media (max-width:820px) {{
      .block-container {{ padding:0.6rem 0.7rem 4rem !important; }}
      .zl-stats {{ grid-template-columns:repeat(2,1fr); gap:7px; }}
      .zl-stat {{ padding:9px 11px; }} .zl-stat .v {{ font-size:16px; }}
      .zl-tf {{ grid-template-columns:repeat(2,1fr); }}
      .stTabs [data-baseweb='tab'] {{ padding:8px 10px !important; font-size:12px !important; }}
      [data-testid='column'] {{ min-width:100% !important; }}
      .zl-lv {{ grid-template-columns:repeat(2,1fr); }}
  }}
</style>
""", unsafe_allow_html=True)


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
    "ladder": list(MTF_LADDER), "preset": "Balanced",
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


# ── profile persistence — so rules survive a reboot ──────────────────

def save_profile():
    r: Rules = st.session_state["rules"]
    try:
        with open(PROFILE, "w", encoding="utf-8") as f:
            json.dump({"rules": {k: getattr(r, k) for k in r.__dataclass_fields__
                                 if not isinstance(getattr(r, k), tuple)},
                       "watch": st.session_state["watch"],
                       "ladder": st.session_state["ladder"],
                       "tf": st.session_state["tf"],
                       "account_size": st.session_state["account_size"],
                       "preset": st.session_state["preset"]}, f, indent=2)
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
    for key in ("watch", "ladder", "tf", "account_size", "preset"):
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
        return False, "Telegram not configured — see the Alerts tab."
    try:
        url = (f"https://api.telegram.org/bot{tok}/sendMessage?chat_id={chat}"
               f"&parse_mode=HTML&text={urllib.parse.quote(text)}")
        ok = json.loads(_get(url).decode()).get("ok", False)
        return ok, "Sent." if ok else "Telegram rejected the message."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


# ── analysis ─────────────────────────────────────────────────────────

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
    origin = origins.get(base, "demo")
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

    return {"symbol": symbol, "tf": base, "decision": dec, "price": price, "atr": a,
            "change": change, "levels": levels, "confluence": conf, "view": view,
            "grade": mtf_grade(dec, view, conf), "frames": frames, "origins": origins,
            "origin": origin, "primary": primary, "d1": d1, "watch": watch,
            "why": explain(dec, view, conf, symbol)}


def run_scan(rules: Rules):
    out, failed = [], []
    watch = st.session_state["watch"]
    bar = st.progress(0.0, text="Scanning…")
    for i, sym in enumerate(watch, 1):
        bar.progress(i / len(watch), text=f"{sym} · {' · '.join(st.session_state['ladder'])}")
        try:
            out.append(analyse(sym, rules, st.session_state["td_key"]))
        except Exception as exc:
            failed.append(f"{sym}: {exc}")
    bar.empty()
    order = {"A": 0, "B": 1, "C": 2, "—": 3}
    out.sort(key=lambda r: (order[r["grade"]], -(r["decision"].rr or 0)))
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


def log_pick(row: dict):
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
            "origin": row["origin"], "outcome": "pending"}) + "\n")


def picks(limit: int = 200):
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
    return (f"<span class='zl-chip' style='background:{c}22;color:{c}'>"
            f"{origin.upper()}</span>")


# ── chart ────────────────────────────────────────────────────────────

def chart(row: dict, rules: Rules, bars: int = 120, show_daily: bool = True) -> go.Figure:
    symbol, df = row["symbol"], row["primary"]
    dig = SYMBOLS[symbol]["digits"]
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
        whiskerwidth=0.2, showlegend=False))

    def band(lo, hi, fill, edge, label, start=None, dash=None):
        if hi < y_lo or lo > y_hi:
            return
        floor_h = (y_hi - y_lo) * 0.014
        if (hi - lo) < floor_h:
            mid = (lo + hi) / 2
            lo, hi = mid - floor_h / 2, mid + floor_h / 2
        fig.add_shape(type="rect", x0=start or t0, x1=right, y0=lo, y1=hi, fillcolor=fill,
                      layer="below", line=dict(color=edge, width=1, dash=dash or "solid"))
        fig.add_annotation(x=start or t0, y=hi, text=f" {label} ", showarrow=False,
                           xanchor="left", yanchor="bottom", bgcolor="rgba(22,24,38,.88)",
                           borderpad=2, font=dict(size=9.5, color=edge, family="Inter"))

    if near_sup:
        band(near_sup.low, near_sup.high, "rgba(95,191,143,.12)", UP,
             f"SUPPORT {near_sup.mid:,.{dig}f}")
    if near_res:
        band(near_res.low, near_res.high, "rgba(224,123,135,.12)", DOWN,
             f"RESISTANCE {near_res.mid:,.{dig}f}")

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
            fig.add_annotation(x=right, y=level, text=f" {tag} {level:,.{dig}f} ",
                               showarrow=False, xanchor="left", yanchor="middle",
                               bgcolor=col, borderpad=2,
                               font=dict(size=9.5, color="#161826", family="Inter"))
    else:
        fig.add_shape(type="line", x0=t0, x1=right, y0=price, y1=price,
                      line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=right, y=price, text=f" {price:,.{dig}f} ", showarrow=False,
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
                   tickformat=f",.{dig}f"))
    return fig


def mtf_panel(row: dict):
    view = row["view"]
    dig = SYMBOLS[row["symbol"]]["digits"]
    col = {"bullish": UP, "bearish": DOWN}.get(view.alignment, WARN)
    cells = ""
    for tf in ["M5", "M15", "M30", "H1", "H4", "D1", "W1"]:
        rd = view.reads.get(tf)
        if not rd:
            continue
        c = {"bullish": UP, "bearish": DOWN}.get(rd.bias, FAINT)
        bits = []
        if rd.structure != "none":
            bits.append(rd.structure)
        if rd.at_zone != "mid-range":
            bits.append(f"at {rd.at_zone}")
        if rd.reversal:
            bits.append(rd.reversal)
        if rd.unfilled_fvgs:
            bits.append(f"{rd.unfilled_fvgs} FVG")
        cells += (f"<div class='zl-tf-cell'><div class='tf'>{tf}</div>"
                  f"<div class='bias' style='color:{c}'>{rd.bias}</div>"
                  f"<div class='zl-muted' style='margin-top:4px;font-size:10.5px'>"
                  f"{' · '.join(bits) or 'no signal'}</div></div>")
    pct = int(view.agreement * 100)
    card(f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px'>"
         f"<span class='zl-kicker'>Timeframe stack</span>"
         f"<span style='margin-left:auto;font-size:13px;color:{col};font-weight:500'>"
         f"{view.alignment.upper()} · {pct}% agreement</span></div>"
         f"<div class='zl-tf'>{cells}</div>"
         f"<div class='zl-bar'><div style='width:{pct}%;height:100%;background:{col}'></div></div>"
         f"<div class='zl-muted' style='margin-top:8px'>{view.summary}</div>")


def why_block(row: dict):
    if not row["why"]:
        return
    items = "".join(f"<div class='zl-why'><span class='n'>{i}</span>"
                    f"<span style='flex:1;font-size:12.5px;line-height:1.5'>{w}</span></div>"
                    for i, w in enumerate(row["why"], 1))
    card(f"<div class='zl-kicker' style='margin-bottom:6px'>Why this trade</div>{items}")


def watch_card(w, symbol: str):
    dig = SYMBOLS[symbol]["digits"]
    col = {"imminent": UP, "watching": WARN}.get(w.urgency, FAINT)
    side = UP if w.direction == "BUY" else DOWN
    dist = pips(symbol, w.distance)
    forming = (f"<div style='margin-top:7px;font-size:12px;color:{UP}'>"
               f"◆ Candle forming: {w.forming}</div>") if w.forming else ""
    card(f"<div style='display:flex;align-items:center;gap:10px'>"
         f"<span class='zl-chip' style='background:{col}22;color:{col}'>{w.urgency.upper()}</span>"
         f"<span style='font-size:14.5px;font-weight:500'>{SYMBOLS[symbol]['mt5']}</span>"
         f"<span style='color:{side};font-size:12px'>{w.direction} setup forming</span>"
         f"<span style='margin-left:auto' class='zl-muted mono'>{dist:g} pips away</span></div>"
         f"<div style='font-size:12.5px;margin-top:8px;line-height:1.5'>"
         f"Price is {w.state} at the {w.zone_kind} "
         f"<span class='mono'>{w.zone_low:,.{dig}f}–{w.zone_high:,.{dig}f}</span>. "
         f"Waiting for {w.waiting_for}.</div>{forming}"
         f"<div class='zl-muted' style='margin-top:7px'>Candle closes in about "
         f"{w.minutes_left} min · structure {w.structure}</div>")


def safe(fn, label):
    try:
        fn()
    except Exception as exc:
        st.error(f"{label}: {type(exc).__name__} — {exc}")
        with st.expander("Details"):
            import traceback
            st.code(traceback.format_exc())


# ── login ────────────────────────────────────────────────────────────

def face_login():
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown(f"""
        <div style='padding:7vh 0 6px'>
          <div style='letter-spacing:.26em;font-size:12px;color:{ACCENT}'>◈ ZONELOCK</div>
          <div style='font-size:33px;font-weight:500;letter-spacing:-.025em;line-height:1.15;
               margin-top:14px'>Finds the zone.<br>You place the trade.</div>
          <div style='color:{MUTED};font-size:13px;line-height:1.6;margin-top:12px;max-width:38ch'>
            Reads every timeframe from five minutes to weekly, marks support, fair value
            gaps and order blocks, tells you why — and hands you the order for MT5.</div>
        </div>""", unsafe_allow_html=True)

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
            if st.button("Create account", use_container_width=True):
                if name and em2 and len(pw2) >= 6:
                    st.session_state.update(user=name, email=em2, stage="app")
                    st.rerun()
                else:
                    st.error("Name, email and a password of 6+ characters.")

        st.markdown("<div class='zl-muted' style='margin-top:12px'>No broker login needed — "
                    "Zonelock never touches your account.</div>", unsafe_allow_html=True)


# ── main ─────────────────────────────────────────────────────────────

def face_app():
    r: Rules = st.session_state["rules"]
    now = datetime.now(timezone.utc)
    events, cal_err = economic_calendar()
    upcoming = next_high_impact(events, now)
    tf_keys = list(TIMEFRAMES.keys())
    scan = st.session_state["scan"]

    with st.sidebar:
        st.markdown(f"<div style='letter-spacing:.24em;font-size:11px;color:{ACCENT};"
                    f"padding:4px 0 2px'>◈ ZONELOCK</div>", unsafe_allow_html=True)
        st.divider()
        st.session_state["watch"] = st.multiselect("Watchlist", list(SYMBOLS.keys()),
                                                   st.session_state["watch"])
        st.session_state["ladder"] = st.multiselect(
            "Timeframes to read", tf_keys, st.session_state["ladder"])
        st.session_state["account_size"] = st.number_input(
            "Account size ($)", 50.0, 1_000_000.0, st.session_state["account_size"], 50.0)
        st.divider()
        if st.button("Save my settings", use_container_width=True):
            st.success("Saved.") if save_profile() else st.warning("Could not save.")

    if not st.session_state["ladder"]:
        st.session_state["ladder"] = ["M15", "H1", "H4", "D1"]

    # ── header with identity and sign out ──
    sessions = [("Tokyo", 0, 9), ("London", 7, 16), ("New York", 12, 21)]
    live_now = [n for n, a, b in sessions if a <= now.hour < b]
    pill = "".join(f"<span class='zl-chip' style='background:{A800 if n in live_now else RAISED};"
                   f"color:{A300 if n in live_now else FAINT}'>{n}</span>"
                   for n, _, _ in sessions)
    scanned = st.session_state["scanned_at"]
    age = f"{int((now - scanned).total_seconds() // 60)}m ago" if scanned else "not yet"

    head, out = st.columns([6, 1])
    with head:
        st.markdown(f"""
        <div class='zl-strip'>
          <div><div style='font-size:18px;font-weight:600;letter-spacing:-.01em'>
              {st.session_state['user'] or 'Trader'}</div>
            <div class='zl-muted' style='margin-top:2px'>{st.session_state['email']} ·
            {st.session_state['preset']} rules · last scan {age}</div></div>
          <div style='margin-left:auto;display:flex;align-items:center;gap:6px;flex-wrap:wrap'>
            {pill}<span class='zl-chip'>{now:%H:%M} UTC</span></div>
        </div>""", unsafe_allow_html=True)
    with out:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            save_profile()
            st.session_state["stage"] = "login"
            st.rerun()

    tabs = st.tabs(["Scanner", "Setup", "Chart", "Market", "Timeframes",
                    "Daily zones", "Picks", "News", "Rules", "Account"])

    def tf_picker(key: str):
        chosen = st.radio("Timeframe", tf_keys, index=tf_keys.index(st.session_state["tf"]),
                          horizontal=True, key=key, label_visibility="collapsed")
        if chosen != st.session_state["tf"]:
            st.session_state["tf"] = chosen
            st.rerun()

    # ── Scanner ──
    def _scanner():
        c1, c2 = st.columns([1, 2.2])
        with c1:
            if st.button("Scan now", use_container_width=True):
                run_scan(r)
                st.rerun()
        with c2:
            tf_picker("tf_scan")

        if upcoming:
            mins = int((upcoming["time"] - now).total_seconds() // 60)
            if mins <= r.news_block_minutes:
                note(f"<b>{upcoming['currency']} {upcoming['title']}</b> in {mins} min — "
                     f"setups on {upcoming['currency']} pairs are news-blocked.", "warn")
            else:
                h, m = divmod(mins, 60)
                note(f"Next high-impact event · <b>{upcoming['currency']} "
                     f"{upcoming['title']}</b> in {h}h {m:02d}m.", "muted")

        if not scan:
            note("Press <b>Scan now</b>. Each symbol is read on every selected timeframe, "
                 "graded A to C, and anything close to a zone appears as a watch so you "
                 "can see it coming.", "accent")
            return

        rows = scan["rows"]
        found = [x for x in rows if x["decision"].taken]
        watching = [x for x in rows if x.get("watch")]
        demo_n = len([x for x in rows if x["origin"] == "demo"])
        a_grade = [x for x in found if x["grade"] == "A"]

        if demo_n:
            note(f"<b>{demo_n} of {len(rows)} symbols are on demo data</b> — the free feeds "
                 f"could not be reached for them from this host. Crypto usually works "
                 f"(Binance); for gold, FX and indices add a free Twelve Data key on the "
                 f"<b>Account</b> tab. Demo rows are marked.", "warn")

        st.markdown(f"""
        <div class='zl-stats'>
          <div class='zl-stat'><div class='k'>Scanned</div><div class='v mono'>{len(rows)}</div>
            <div class='s'>× {len(st.session_state['ladder'])} timeframes</div></div>
          <div class='zl-stat'><div class='k'>Setups</div>
            <div class='v mono' style='color:{UP if found else MUTED}'>{len(found)}</div>
            <div class='s'>ready to place</div></div>
          <div class='zl-stat'><div class='k'>Watching</div>
            <div class='v mono' style='color:{WARN if watching else MUTED}'>{len(watching)}</div>
            <div class='s'>at or near a zone</div></div>
          <div class='zl-stat'><div class='k'>A-grade</div>
            <div class='v mono' style='color:{UP if a_grade else MUTED}'>{len(a_grade)}</div>
            <div class='s'>best confluence</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("##### Setups ready")
        if not found:
            note("Nothing qualifies yet — the system only calls a setup when price is at "
                 "a zone <i>and</i> a candle has confirmed the turn.", "muted")

        for row in found:
            d, sym = row["decision"], row["symbol"]
            dig, g, gc = SYMBOLS[sym]["digits"], row["grade"], GRADE[row["grade"]]
            side = UP if d.direction == "BUY" else DOWN
            v = row["view"]
            al_col = UP if v.agrees_with(d.direction) else (WARN if v.alignment == "mixed" else DOWN)
            rp = pips(sym, abs(d.entry - d.stop_loss))
            wp = pips(sym, abs(d.take_profit - d.entry))
            tags = "".join(f"<span class='zl-chip'>{t}</span>" for t in d.tags)
            card(f"""
              <div style='display:flex;align-items:center;gap:11px'>
                <span class='zl-grade' style='background:{gc}22;color:{gc}'>{g}</span>
                <div style='flex:1'>
                  <div style='font-size:15.5px;font-weight:500'>{SYMBOLS[sym]['mt5']}
                    <span style='color:{side};font-size:12.5px;margin-left:6px'>{d.direction}</span>
                    <span class='zl-muted' style='font-size:11.5px;margin-left:6px'>{row['tf']}</span></div>
                  <div class='zl-muted' style='margin-top:2px'>{SYMBOLS[sym]['name']} ·
                    {SYMBOLS[sym]['class']}</div>
                </div>
                <div style='text-align:right'>
                  <div class='mono' style='font-size:15px'>{d.rr}R</div>
                  <div class='zl-muted'>{d.lots:.2f} lots</div>
                </div>
              </div>
              <div style='font-size:13px;margin-top:9px;line-height:1.45'>{d.headline}</div>
              <div style='margin-top:8px'>{tags}
                <span class='zl-chip' style='background:{al_col}22;color:{al_col}'>
                  stack {v.alignment} {int(v.agreement*100)}%</span>{origin_chip(row['origin'])}</div>
              <div class='zl-lv'>
                <div><div class='k'>Entry</div><div class='v mono'>{d.entry:,.{dig}f}</div></div>
                <div><div class='k'>Stop · {rp:g} pips</div>
                  <div class='v mono' style='color:{DOWN}'>{d.stop_loss:,.{dig}f}</div></div>
                <div><div class='k'>Target · {wp:g} pips</div>
                  <div class='v mono' style='color:{UP}'>{d.take_profit:,.{dig}f}</div></div>
                <div><div class='k'>Daily confluence</div><div class='v' style='font-size:12px'>
                  {' · '.join(row['confluence']) if row['confluence'] else 'none'}</div></div>
              </div>""")
            b1, b2, b3 = st.columns(3)
            if b1.button("Full detail", key=f"o{sym}", use_container_width=True):
                st.session_state["symbol"] = sym
                st.rerun()
            if b2.button("Log pick", key=f"l{sym}", use_container_width=True):
                log_pick(row)
                st.success(f"{sym} logged.")
            if b3.button("Telegram", key=f"t{sym}", use_container_width=True):
                ok, msg = telegram(ticket_text(row))
                st.success(msg) if ok else st.warning(msg)

        if watching:
            st.markdown("##### Watching — reversal not confirmed yet")
            st.markdown("<div class='zl-muted' style='margin-bottom:8px'>Price is at or "
                        "approaching a zone. These become setups the moment a reversal "
                        "candle closes.</div>", unsafe_allow_html=True)
            for row in sorted(watching, key=lambda x: {"imminent": 0, "watching": 1,
                                                       "approaching": 2}[x["watch"].urgency]):
                watch_card(row["watch"], row["symbol"])

        passed = [x for x in rows if not x["decision"].taken and not x.get("watch")]
        if passed:
            with st.expander(f"Why {len(passed)} symbols were passed entirely"):
                for row in passed:
                    d = row["decision"]
                    st.markdown(f"<div class='zl-row'><span class='zl-chip'>{row['symbol']}</span>"
                                f"<span style='flex:1;font-size:12.5px'>{d.headline}</span>"
                                f"<span style='color:{DOWN};font-size:11px'>{d.verdict}</span></div>",
                                unsafe_allow_html=True)

        if scan["failed"]:
            with st.expander(f"{len(scan['failed'])} symbols failed entirely"):
                for f in scan["failed"]:
                    st.markdown(f"<div class='zl-muted'>{f}</div>", unsafe_allow_html=True)

    # ── Setup ──
    def _setup():
        c1, c2 = st.columns([1, 2])
        with c1:
            sym = st.selectbox("Symbol", list(SYMBOLS.keys()),
                               index=list(SYMBOLS.keys()).index(st.session_state["symbol"]))
            st.session_state["symbol"] = sym
        with c2:
            tf_picker("tf_setup")

        row = cached_row(sym, r)
        d, meta, dig = row["decision"], SYMBOLS[sym], SYMBOLS[sym]["digits"]

        if row["origin"] == "demo":
            note("This symbol is on <b>demo data</b> — the analysis is real but the prices "
                 "are generated. Add a free Twelve Data key on the Account tab.", "warn")

        if not d.taken:
            card(f"<div class='zl-kicker'>{meta['mt5']} · {row['tf']} · no setup</div>"
                 f"<div style='font-size:15px;margin-top:6px;line-height:1.4'>{d.headline}</div>"
                 f"<div class='zl-muted' style='margin-top:6px'>Stopped by "
                 f"<span style='color:{DOWN}'>{d.verdict}</span></div>")
            if row.get("watch"):
                watch_card(row["watch"], sym)
            mtf_panel(row)
            checks = "".join(
                f"<div class='zl-row'><span style='color:{UP if c.passed else DOWN};width:14px'>"
                f"{'✓' if c.passed else '✕'}</span><span style='flex:1;font-size:12.5px'>{c.label}</span>"
                f"<span class='zl-muted mono' style='font-size:11px'>{c.value}</span></div>"
                for c in d.checks)
            card(f"<div class='zl-kicker' style='margin-bottom:4px'>Rule checks</div>{checks}")
            return

        rp = pips(sym, abs(d.entry - d.stop_loss))
        wp = pips(sym, abs(d.take_profit - d.entry))
        g, gc, v = row["grade"], GRADE[row["grade"]], row["view"]
        risk_cash = st.session_state["account_size"] * r.risk_percent / 100

        st.markdown(f"""
        <div class='zl-card' style='border-color:{gc}44'>
          <div style='display:flex;align-items:center;gap:12px'>
            <span class='zl-grade' style='background:{gc}22;color:{gc};width:38px;height:38px;
                  font-size:17px'>{g}</span>
            <div style='flex:1'>
              <div style='font-size:20px;font-weight:500'>{meta['mt5']} ·
                <span style='color:{UP if d.direction=="BUY" else DOWN}'>{d.direction}</span></div>
              <div class='zl-muted'>{meta['name']} · {row['tf']} · {d.rr}R · stack {v.alignment}</div>
            </div>
          </div>
          <div style='font-size:13.5px;margin-top:11px;line-height:1.5'>{d.headline}</div>
          <div class='zl-lv'>
            <div><div class='k'>Risk</div><div class='v mono' style='color:{DOWN}'>{rp:g} pips</div></div>
            <div><div class='k'>Reward</div><div class='v mono' style='color:{UP}'>{wp:g} pips</div></div>
            <div><div class='k'>At risk</div><div class='v mono'>${risk_cash:,.2f}</div></div>
            <div><div class='k'>If it wins</div><div class='v mono' style='color:{UP}'>
              ${risk_cash * (d.rr or 0):,.2f}</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

        why_block(row)

        st.markdown("##### Place this on MT5")
        st.markdown(f"""
        <div class='zl-ticket'>
          Symbol &nbsp;&nbsp;&nbsp; <b>{meta['mt5']}</b><br>
          Type &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b style='color:{UP if d.direction=="BUY" else DOWN}'>
            Market {d.direction}</b><br>
          Volume &nbsp;&nbsp;&nbsp; <b>{d.lots:.2f}</b> lots<br>
          Stop loss &nbsp;<b style='color:{DOWN}'>{d.stop_loss:,.{dig}f}</b>
            <span style='color:{MUTED}'>&nbsp; ({rp:g} pips)</span><br>
          Take profit <b style='color:{UP}'>{d.take_profit:,.{dig}f}</b>
            <span style='color:{MUTED}'>&nbsp; ({wp:g} pips)</span>
        </div>""", unsafe_allow_html=True)
        st.code(f"{meta['mt5']}  {d.direction}  {d.lots:.2f}  "
                f"SL {d.stop_loss:,.{dig}f}  TP {d.take_profit:,.{dig}f}", language=None)
        st.caption(f"Entry at market while price holds the zone; otherwise a limit at "
                   f"{d.entry:,.{dig}f}. {spread_note(row['origin'])}")

        c1, c2 = st.columns(2)
        if c1.button("Log this pick", use_container_width=True, key="setup_log"):
            log_pick(row)
            st.success("Logged.")
        if c2.button("Send to Telegram", use_container_width=True, key="setup_tg"):
            ok, msg = telegram(ticket_text(row))
            st.success(msg) if ok else st.warning(msg)

        mtf_panel(row)
        checks = "".join(
            f"<div class='zl-row'><span style='color:{UP if c.passed else DOWN};width:14px'>"
            f"{'✓' if c.passed else '✕'}</span><span style='flex:1;font-size:12.5px'>{c.label}</span>"
            f"<span class='zl-muted mono' style='font-size:11px'>{c.value}</span></div>"
            for c in d.checks)
        card(f"<div class='zl-kicker' style='margin-bottom:4px'>Every rule checked</div>{checks}")

    # ── Chart ──
    def _chart():
        c1, c2 = st.columns([1, 2])
        with c1:
            sym = st.selectbox("Symbol", list(SYMBOLS.keys()),
                               index=list(SYMBOLS.keys()).index(st.session_state["symbol"]),
                               key="chart_sym")
            st.session_state["symbol"] = sym
        with c2:
            tf_picker("tf_chart")

        c3, c4 = st.columns([2, 1])
        span = c3.radio("Bars", [60, 120, 200, 300], index=1, horizontal=True,
                        label_visibility="collapsed")
        show_daily = c4.toggle("Daily levels", True)

        row = cached_row(sym, r)
        age = cache_age(sym, row["tf"])
        st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin:2px 0 6px'>"
                    f"<span style='font-size:13px'>{SYMBOLS[sym]['mt5']} · "
                    f"{TIMEFRAMES[row['tf']]['label']}</span>"
                    f"<span class='mono' style='font-size:15px'>"
                    f"{row['price']:,.{SYMBOLS[sym]['digits']}f}</span>"
                    f"<span class='mono' style='font-size:12px;color:"
                    f"{UP if row['change']>=0 else DOWN}'>{row['change']:+.2f}%</span>"
                    f"<span style='margin-left:auto'>{origin_chip(row['origin'])}</span>"
                    + (f"<span class='zl-muted'>{age//60}m old</span>" if age else "")
                    + "</div>", unsafe_allow_html=True)
        st.plotly_chart(chart(row, r, span, show_daily), use_container_width=True,
                        config={"displayModeBar": False, "scrollZoom": True})
        legend = "".join(f"<span class='zl-chip'><span style='color:{c}'>■</span> {t}</span>"
                         for c, t in [(UP, "Support"), (DOWN, "Resistance"),
                                      (A300, "Fair value gap"), (ACCENT, "Order block"),
                                      (FAINT, "Daily levels")])
        st.markdown(f"<div style='margin-top:6px'>{legend}</div>", unsafe_allow_html=True)
        if row.get("watch"):
            watch_card(row["watch"], sym)

    # ── Market ──
    def _market():
        st.markdown("##### Sessions")
        cells = ""
        for name, a, b in sessions:
            on = a <= now.hour < b
            if on:
                pct = (now.hour - a) / max(b - a, 1)
                sub = f"closes in {b - now.hour}h"
            else:
                nxt = (a - now.hour) % 24
                pct, sub = 0, f"opens in {nxt}h"
            c = ACCENT if on else FAINT
            cells += (f"<div class='zl-mkt-cell'><div style='display:flex;align-items:center;gap:6px'>"
                      f"<span style='width:6px;height:6px;border-radius:50%;background:{c}'></span>"
                      f"<span style='font-size:13px'>{name}</span></div>"
                      f"<div class='zl-muted' style='margin:4px 0 6px'>{a:02d}:00–{b:02d}:00 UTC · {sub}</div>"
                      f"<div class='zl-bar' style='margin:0'><div style='width:{pct*100:.0f}%;"
                      f"height:100%;background:{c}'></div></div></div>")
        st.markdown(f"<div class='zl-mkt'>{cells}</div>", unsafe_allow_html=True)

        st.markdown("##### Watchlist")
        if not scan:
            note("Run a scan to populate the market view.", "muted")
        else:
            cells = ""
            for row in sorted(scan["rows"], key=lambda x: -abs(x["change"])):
                sym = row["symbol"]
                dig = SYMBOLS[sym]["digits"]
                c = UP if row["change"] >= 0 else DOWN
                v = row["view"]
                bc = {"bullish": UP, "bearish": DOWN}.get(v.alignment, WARN)
                state = ("SETUP" if row["decision"].taken else
                         row["watch"].urgency.upper() if row.get("watch") else "—")
                sc = (UP if row["decision"].taken else
                      WARN if row.get("watch") else FAINT)
                cells += (f"<div class='zl-mkt-cell'>"
                          f"<div style='display:flex;align-items:baseline;gap:6px'>"
                          f"<span style='font-size:13px;font-weight:500'>{SYMBOLS[sym]['mt5']}</span>"
                          f"<span style='margin-left:auto;font-size:9.5px;color:{sc}'>{state}</span></div>"
                          f"<div class='mono' style='font-size:17px;margin-top:4px'>"
                          f"{row['price']:,.{dig}f}</div>"
                          f"<div class='mono' style='font-size:11.5px;color:{c}'>"
                          f"{row['change']:+.2f}%</div>"
                          f"<div class='zl-muted' style='margin-top:6px;font-size:10.5px'>"
                          f"<span style='color:{bc}'>{v.alignment}</span> · "
                          f"{int(v.agreement*100)}% · {row['origin']}</div></div>")
            st.markdown(f"<div class='zl-mkt'>{cells}</div>", unsafe_allow_html=True)

        st.markdown("##### Volatility now")
        if scan:
            for row in sorted(scan["rows"], key=lambda x: -(x["atr"] / max(x["price"], 1e-9))):
                sym = row["symbol"]
                pct = row["atr"] / max(row["price"], 1e-9) * 100
                st.markdown(f"<div class='zl-row'>"
                            f"<span class='zl-chip'>{SYMBOLS[sym]['mt5']}</span>"
                            f"<span style='flex:1;font-size:12.5px'>{SYMBOLS[sym]['name']}</span>"
                            f"<span class='zl-muted mono' style='font-size:11px'>"
                            f"ATR {pips(sym, row['atr']):g} pips</span>"
                            f"<div style='width:90px;height:5px;border-radius:3px;background:{RAISED};"
                            f"overflow:hidden'><div style='width:{min(pct*40,100):.0f}%;height:100%;"
                            f"background:{ACCENT}'></div></div></div>", unsafe_allow_html=True)

    # ── Timeframes ──
    def _timeframes():
        sym = st.selectbox("Symbol", list(SYMBOLS.keys()),
                           index=list(SYMBOLS.keys()).index(st.session_state["symbol"]),
                           key="mtf_sym")
        st.session_state["symbol"] = sym
        row = cached_row(sym, r)
        mtf_panel(row)
        st.markdown("##### Every timeframe in detail")
        dig = SYMBOLS[sym]["digits"]
        for tf in ["M5", "M15", "M30", "H1", "H4", "D1", "W1"]:
            rd = row["view"].reads.get(tf)
            if not rd:
                continue
            c = {"bullish": UP, "bearish": DOWN}.get(rd.bias, WARN)
            sup = f"{rd.nearest_support:,.{dig}f}" if rd.nearest_support else "—"
            res = f"{rd.nearest_resistance:,.{dig}f}" if rd.nearest_resistance else "—"
            card(f"<div style='display:flex;align-items:center;gap:10px'>"
                 f"<span class='zl-chip' style='background:{c}22;color:{c}'>{tf}</span>"
                 f"<span style='flex:1;font-size:13.5px'>{TIMEFRAMES[tf]['label']} · "
                 f"<b style='color:{c}'>{rd.bias}</b></span>"
                 f"<span class='zl-muted' style='font-size:11px'>{rd.structure}</span></div>"
                 f"<div class='zl-lv'>"
                 f"<div><div class='k'>At</div><div class='v' style='font-size:12.5px'>{rd.at_zone}</div></div>"
                 f"<div><div class='k'>Support</div><div class='v mono' style='font-size:12.5px'>{sup}</div></div>"
                 f"<div><div class='k'>Resistance</div><div class='v mono' style='font-size:12.5px'>{res}</div></div>"
                 f"<div><div class='k'>Signals</div><div class='v' style='font-size:12px'>"
                 f"{rd.reversal or '—'}"
                 f"{' · ' + str(rd.unfilled_fvgs) + ' FVG' if rd.unfilled_fvgs else ''}"
                 f"{' · ' + rd.order_block if rd.order_block else ''}</div></div></div>")

    # ── Daily zones ──
    def _daily():
        sym = st.session_state["symbol"]
        row = cached_row(sym, r)
        dig, price = SYMBOLS[sym]["digits"], row["price"]
        st.markdown(f"##### {SYMBOLS[sym]['mt5']} · daily map")
        st.markdown(f"<div class='zl-muted' style='margin-bottom:10px'>Levels from daily "
                    f"candles — mark these first. Price now "
                    f"<b class='mono'>{price:,.{dig}f}</b>.</div>", unsafe_allow_html=True)
        if not row["levels"]:
            note("Daily candles unavailable for this symbol right now.", "warn")
            return
        for lv in row["levels"]:
            col = {"resistance": DOWN, "support": UP}.get(lv.kind, FAINT)
            st.markdown(f"<div class='zl-row'>"
                        f"<span class='zl-chip' style='background:{col}22;color:{col}'>"
                        f"{lv.kind[:3].upper()}</span>"
                        f"<span style='flex:1;font-size:13px'>{lv.name}</span>"
                        f"<span class='mono' style='font-size:13px'>{lv.price:,.{dig}f}</span>"
                        f"<span class='zl-muted mono' style='font-size:11px;width:110px;"
                        f"text-align:right'>{pips(sym, lv.distance(price)):g} pips "
                        f"{'above' if lv.price > price else 'below'}</span></div>",
                        unsafe_allow_html=True)

    # ── Picks ──
    def _picks():
        rows = picks()
        if not rows:
            note("No picks logged yet. Log one from the Scanner or Setup tab and it "
                 "appears here with the full reasoning.", "muted")
            return
        wins = len([x for x in rows if x.get("outcome") == "win"])
        st.markdown(f"""
        <div class='zl-stats'>
          <div class='zl-stat'><div class='k'>Logged</div><div class='v mono'>{len(rows)}</div>
            <div class='s'>picks recorded</div></div>
          <div class='zl-stat'><div class='k'>A-grade</div>
            <div class='v mono'>{len([x for x in rows if x['grade']=='A'])}</div>
            <div class='s'>highest confluence</div></div>
          <div class='zl-stat'><div class='k'>Avg R:R</div>
            <div class='v mono'>{sum(x.get('rr') or 0 for x in rows)/max(len(rows),1):.2f}</div>
            <div class='s'>as planned</div></div>
          <div class='zl-stat'><div class='k'>Avg risk</div>
            <div class='v mono'>{sum(x.get('risk_pips') or 0 for x in rows)/max(len(rows),1):.0f}</div>
            <div class='s'>pips per trade</div></div>
        </div>""", unsafe_allow_html=True)

        st.dataframe(pd.DataFrame([{
            "When": x["at"][5:16].replace("T", " "), "Symbol": x["mt5"],
            "TF": x.get("tf", ""), "Grade": x["grade"], "Side": x["direction"],
            "Entry": x["entry"], "SL": x["sl"], "TP": x["tp"],
            "Risk pips": x.get("risk_pips"), "Reward pips": x.get("reward_pips"),
            "R:R": x["rr"], "Lots": x["lots"]} for x in rows]),
            use_container_width=True, hide_index=True)

        st.markdown("##### Full reasoning")
        for x in rows[:25]:
            with st.expander(f"{x['mt5']} {x['direction']} · {x['grade']}-grade · "
                             f"{x.get('tf','')} · {x['at'][5:16]}"):
                st.write(x["headline"])
                if x.get("why"):
                    st.markdown("".join(
                        f"<div class='zl-why'><span class='n'>{i}</span>"
                        f"<span style='flex:1;font-size:12.5px;line-height:1.5'>{w}</span></div>"
                        for i, w in enumerate(x["why"], 1)), unsafe_allow_html=True)
                st.markdown("".join(f"<span class='zl-chip'>{t}</span>" for t in x["tags"]),
                            unsafe_allow_html=True)

    # ── News ──
    def _news():
        t1, t2 = st.tabs(["Economic calendar", "Headlines"])
        with t1:
            if cal_err:
                note(f"Live calendar could not load — {cal_err}.", "warn")
            ahead = [e for e in events if e["time"] > now][:14]
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
                     f"<div class='zl-muted' style='margin-top:4px'>{h['source']} · "
                     f"{h['when']}</div>")

    # ── Rules ──
    def _rules():
        st.markdown("##### Preset")
        chosen = st.radio("Preset", list(PRESETS.keys()),
                          index=list(PRESETS.keys()).index(st.session_state["preset"]),
                          horizontal=True, label_visibility="collapsed",
                          captions=["1% · 2R min · strict", "2% · 1.5R min",
                                    "3% · 1.3R min · loose"])
        if chosen != st.session_state["preset"]:
            apply_preset(chosen)
            st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Entry rules")
            r.require_reversal_candle = st.toggle("Require a reversal candle",
                                                  r.require_reversal_candle,
                                                  help="No candle confirmation, no trade.")
            r.require_fvg_unfilled = st.toggle("Fair value gap must be unfilled",
                                               r.require_fvg_unfilled)
            r.require_ob_structure = st.toggle("Order block needs BOS", r.require_ob_structure)
            r.accept_choch = st.toggle("Accept CHoCH reversals", r.accept_choch)
            r.min_zone_touches = st.slider("Minimum zone touches", 1, 5, r.min_zone_touches,
                                           help="How many times price must have respected "
                                                "a level before it counts as a zone.")
            r.zone_atr_mult = st.slider("Zone thickness (× ATR)", 0.1, 1.0,
                                        float(r.zone_atr_mult), 0.05)
            r.swing_lookback = st.slider("Swing lookback (bars each side)", 2, 8,
                                         r.swing_lookback)
            r.min_fvg_atr = st.slider("Ignore gaps smaller than (× ATR)", 0.0, 1.0,
                                      float(r.min_fvg_atr), 0.05)
        with c2:
            st.markdown("##### Risk and sizing")
            r.base_lot = st.number_input("Base lot size", 0.01, 5.0, r.base_lot, 0.01,
                                         format="%.2f")
            r.risk_percent = st.slider("Risk per trade (%)", 0.5, 5.0, r.risk_percent, 0.25)
            r.min_rr = st.slider("Minimum reward to risk", 1.0, 4.0, r.min_rr, 0.1)
            r.max_open_positions = st.slider("Max open positions", 1, 10, r.max_open_positions)
            r.daily_profit_cap = st.number_input("Daily profit cap ($)", 0.0, 5000.0,
                                                 r.daily_profit_cap, 5.0)
            r.max_daily_loss = st.number_input("Max daily loss ($)", 0.0, 5000.0,
                                               r.max_daily_loss, 5.0)
            st.markdown("##### Timing")
            r.news_block_minutes = st.slider("News blackout (min either side)", 0, 120,
                                             r.news_block_minutes, 5)
            r.session_filter = st.toggle("Session-aware volatility", r.session_filter)

        st.session_state["rules"] = r
        c1, c2 = st.columns(2)
        if c1.button("Save these rules", use_container_width=True):
            st.success("Saved — they load next time you sign in.") if save_profile() \
                else st.warning("Could not save.")
        if c2.button("Re-scan with these rules", use_container_width=True):
            run_scan(r)
            st.rerun()

    # ── Account ──
    def _account():
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown("##### Profile")
            card(f"<div style='display:flex;align-items:center;gap:12px'>"
                 f"<div style='width:40px;height:40px;border-radius:50%;background:{A800};"
                 f"display:grid;place-items:center;color:{A300};font-size:15px'>"
                 f"{(st.session_state['user'] or 'T')[0].upper()}</div>"
                 f"<div style='flex:1'><div style='font-size:15px'>"
                 f"{st.session_state['user'] or 'Trader'}</div>"
                 f"<div class='zl-muted'>{st.session_state['email']}</div></div></div>"
                 f"<div class='zl-lv'>"
                 f"<div><div class='k'>Preset</div><div class='v' style='font-size:13px'>"
                 f"{st.session_state['preset']}</div></div>"
                 f"<div><div class='k'>Account</div><div class='v mono' style='font-size:13px'>"
                 f"${st.session_state['account_size']:,.0f}</div></div>"
                 f"<div><div class='k'>Symbols</div><div class='v' style='font-size:13px'>"
                 f"{len(st.session_state['watch'])}</div></div>"
                 f"<div><div class='k'>Picks</div><div class='v' style='font-size:13px'>"
                 f"{len(picks())}</div></div></div>")
            if st.button("Sign out of Zonelock", use_container_width=True, key="acc_out"):
                save_profile()
                st.session_state["stage"] = "login"
                st.rerun()

            st.markdown("##### Market data")
            note("Crypto comes from <b>Binance</b> — free, no key, reliable from any host. "
                 "Gold, FX, indices and oil need a key when Yahoo blocks the server, which "
                 "it does on most cloud hosts.<br><br>"
                 "Get a free key at <b>twelvedata.com</b> — 800 calls a day, no card.",
                 "accent")
            st.session_state["td_key"] = st.text_input(
                "Twelve Data API key", st.session_state["td_key"], type="password")
            if st.button("Test the key"):
                try:
                    df, origin = fetch("XAUUSD", "M15", 100, st.session_state["td_key"],
                                       allow_demo=False)
                    st.success(f"Working — gold via {origin}, "
                               f"last {float(df['close'].iloc[-1]):,.2f}")
                except Exception as exc:
                    st.warning(f"Still failing: {exc}")

        with c2:
            st.markdown("##### Telegram alerts")
            note("1 · Message <b>@BotFather</b>, send <code>/newbot</code>, copy the token."
                 "<br>2 · Message your bot once.<br>3 · Message <b>@userinfobot</b> for your "
                 "chat id.", "muted")
            st.session_state["tg_token"] = st.text_input("Bot token",
                                                         st.session_state["tg_token"],
                                                         type="password")
            st.session_state["tg_chat"] = st.text_input("Chat id", st.session_state["tg_chat"])
            if st.button("Send a test message"):
                ok, msg = telegram("<b>Zonelock</b>\nAlerts are working.")
                st.success(msg) if ok else st.warning(msg)

            st.markdown("##### Scanning while closed")
            st.markdown("<div class='zl-muted'>Run <code>scanner.py</code> on GitHub "
                        "Actions every 15 minutes — same rules, same Telegram chat, "
                        "nothing open. See SCANNER.md.</div>", unsafe_allow_html=True)

            st.markdown("##### Settings")
            if st.button("Save everything now", use_container_width=True, key="acc_save"):
                st.success("Saved.") if save_profile() else st.warning("Could not save.")
            if st.button("Reload saved settings", use_container_width=True):
                st.success("Loaded.") if load_profile() else st.info("Nothing saved yet.")
                st.rerun()

    fns = [_scanner, _setup, _chart, _market, _timeframes, _daily, _picks,
           _news, _rules, _account]
    labels = ["Scanner", "Setup", "Chart", "Market", "Timeframes", "Daily zones",
              "Picks", "News", "Rules", "Account"]
    for tab, fn, label in zip(tabs, fns, labels):
        with tab:
            safe(fn, label)


{"login": face_login, "app": face_app}[st.session_state["stage"]]()
