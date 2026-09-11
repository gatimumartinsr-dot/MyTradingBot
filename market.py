"""
market.py — free market data that works from a cloud host.

Yahoo Finance rate-limits datacenter IPs hard (HTTP 429 on everything), which
is exactly what Streamlit Cloud is. So this module does not depend on any one
provider: it tries several in order of reliability-from-cloud, caches to disk,
and falls back to a clearly-labelled demo series rather than showing the user
a red error.

    from market import SYMBOLS, TIMEFRAMES, fetch
    df, origin = fetch("XAUUSD", "M15")

`origin` is always one of: binance · stooq · twelvedata · yahoo · cache · demo
Show it. The user must always know whether they are looking at real prices.
"""

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

# ── watchlist ────────────────────────────────────────────────────────
# binance: spot pair (no key, works from any IP)
# stooq:   daily history code (no key, works from cloud)
# yahoo:   last resort

SYMBOLS: Dict[str, Dict] = {
    "XAUUSD": {"name": "Gold",          "mt5": "XAUUSDm", "class": "Metals",    "pip": 0.10,   "digits": 2, "binance": "PAXGUSDT", "stooq": "xauusd", "yahoo": "GC=F"},
    "EURUSD": {"name": "Euro",          "mt5": "EURUSDm", "class": "FX majors", "pip": 0.0001, "digits": 5, "binance": "EURUSDT",  "stooq": "eurusd", "yahoo": "EURUSD=X"},
    "GBPUSD": {"name": "Pound",         "mt5": "GBPUSDm", "class": "FX majors", "pip": 0.0001, "digits": 5, "binance": "GBPUSDT",  "stooq": "gbpusd", "yahoo": "GBPUSD=X"},
    "USDJPY": {"name": "Dollar-Yen",    "mt5": "USDJPYm", "class": "FX majors", "pip": 0.01,   "digits": 3, "binance": "",         "stooq": "usdjpy", "yahoo": "USDJPY=X"},
    "AUDUSD": {"name": "Aussie",        "mt5": "AUDUSDm", "class": "FX majors", "pip": 0.0001, "digits": 5, "binance": "",         "stooq": "audusd", "yahoo": "AUDUSD=X"},
    "USDCAD": {"name": "Dollar-Loonie", "mt5": "USDCADm", "class": "FX majors", "pip": 0.0001, "digits": 5, "binance": "",         "stooq": "usdcad", "yahoo": "USDCAD=X"},
    "US30":   {"name": "Dow 30",        "mt5": "US30m",   "class": "Indices",   "pip": 1.0,    "digits": 1, "binance": "",         "stooq": "^dji",   "yahoo": "YM=F"},
    "NAS100": {"name": "Nasdaq 100",    "mt5": "NAS100m", "class": "Indices",   "pip": 1.0,    "digits": 1, "binance": "",         "stooq": "^ndq",   "yahoo": "NQ=F"},
    "SPX500": {"name": "S&P 500",       "mt5": "US500m",  "class": "Indices",   "pip": 0.25,   "digits": 2, "binance": "",         "stooq": "^spx",   "yahoo": "ES=F"},
    "BTCUSD": {"name": "Bitcoin",       "mt5": "BTCUSDm", "class": "Crypto",    "pip": 1.0,    "digits": 1, "binance": "BTCUSDT",  "stooq": "",       "yahoo": "BTC-USD"},
    "ETHUSD": {"name": "Ethereum",      "mt5": "ETHUSDm", "class": "Crypto",    "pip": 0.1,    "digits": 2, "binance": "ETHUSDT",  "stooq": "",       "yahoo": "ETH-USD"},
    "USOIL":  {"name": "WTI Crude",     "mt5": "USOILm",  "class": "Energy",    "pip": 0.01,   "digits": 2, "binance": "",         "stooq": "cl.f",   "yahoo": "CL=F"},
}

TIMEFRAMES: Dict[str, Dict] = {
    "M5":  {"minutes": 5,     "label": "5 minute",  "ttl": 180,  "binance": "5m",  "yahoo": ("5m", "5d"),   "td": "5min"},
    "M15": {"minutes": 15,    "label": "15 minute", "ttl": 300,  "binance": "15m", "yahoo": ("15m", "1mo"), "td": "15min"},
    "M30": {"minutes": 30,    "label": "30 minute", "ttl": 600,  "binance": "30m", "yahoo": ("30m", "1mo"), "td": "30min"},
    "H1":  {"minutes": 60,    "label": "1 hour",    "ttl": 900,  "binance": "1h",  "yahoo": ("1h", "3mo"),  "td": "1h"},
    "H4":  {"minutes": 240,   "label": "4 hour",    "ttl": 1800, "binance": "4h",  "yahoo": ("1h", "6mo"),  "td": "4h", "resample": "4h"},
    "D1":  {"minutes": 1440,  "label": "Daily",     "ttl": 3600, "binance": "1d",  "yahoo": ("1d", "2y"),   "td": "1day"},
    "W1":  {"minutes": 10080, "label": "Weekly",    "ttl": 7200, "binance": "1w",  "yahoo": ("1wk", "5y"),  "td": "1week"},
}

MTF_LADDER = ["M15", "H1", "H4", "D1"]

CACHE_DIR = os.environ.get("ZONELOCK_CACHE", ".zlcache")
MIN_GAP = 0.35
_lock = threading.Lock()
_last = [0.0]


class DataError(RuntimeError):
    pass


# ── HTTP ─────────────────────────────────────────────────────────────

def _throttle():
    with _lock:
        wait = MIN_GAP - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()


def _get(url: str, tries: int = 2, timeout: int = 12) -> bytes:
    delay = 1.2
    for attempt in range(tries):
        _throttle()
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
            "Accept": "application/json,text/csv,*/*",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise DataError(f"HTTP {e.code}") from None
        except Exception as e:
            if attempt < tries - 1:
                time.sleep(delay)
                continue
            raise DataError(str(e)[:60]) from None
    raise DataError("retries exhausted")


# ── disk cache ───────────────────────────────────────────────────────

def _path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, "".join(c if c.isalnum() else "_" for c in key) + ".json")


def _cache_read(key: str, ttl: float) -> Optional[pd.DataFrame]:
    p = _path(key)
    try:
        if time.time() - os.path.getmtime(p) > ttl:
            return None
        with open(p, encoding="utf-8") as f:
            payload = json.load(f)
        df = pd.DataFrame(payload)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df if len(df) >= 60 else None
    except Exception:
        return None


def _cache_write(key: str, df: pd.DataFrame):
    try:
        out = df.copy()
        out["time"] = out["time"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        with open(_path(key), "w", encoding="utf-8") as f:
            json.dump(out.to_dict("records"), f)
    except Exception:
        pass


def cache_age(symbol: str, timeframe: str) -> Optional[int]:
    try:
        return int(time.time() - os.path.getmtime(_path(f"{symbol}_{timeframe}")))
    except Exception:
        return None


# ── providers ────────────────────────────────────────────────────────

def binance(pair: str, interval: str, limit: int) -> pd.DataFrame:
    """No key, no rate-limit problem from cloud hosts. Crypto and a few FX."""
    if not pair:
        raise DataError("no Binance pair")
    url = (f"https://api.binance.com/api/v3/klines?symbol={pair}"
           f"&interval={interval}&limit={min(limit,1000)}")
    rows = json.loads(_get(url).decode())
    if not rows:
        raise DataError("binance empty")
    df = pd.DataFrame([{
        "time": pd.to_datetime(r[0], unit="ms", utc=True),
        "open": float(r[1]), "high": float(r[2]),
        "low": float(r[3]), "close": float(r[4]),
    } for r in rows])
    return df.sort_values("time").reset_index(drop=True)


def stooq(code: str, limit: int, daily_only: bool = True) -> pd.DataFrame:
    """Free daily history, reachable from cloud IPs."""
    if not code:
        raise DataError("no Stooq code")
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(code)}&i=d"
    text = _get(url).decode(errors="replace").strip()
    lines = [l for l in text.splitlines() if l and "," in l]
    if len(lines) < 40:
        raise DataError("stooq empty")
    rows = []
    for line in lines[1:]:
        p = line.split(",")
        if len(p) < 5:
            continue
        try:
            rows.append({"time": p[0], "open": float(p[1]), "high": float(p[2]),
                         "low": float(p[3]), "close": float(p[4])})
        except ValueError:
            continue
    if len(rows) < 40:
        raise DataError("stooq unparseable")
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    return df.dropna().sort_values("time").tail(limit).reset_index(drop=True)


def twelve_data(symbol: str, key: str, interval: str, limit: int) -> pd.DataFrame:
    pair = symbol[:3] + "/" + symbol[3:] if len(symbol) == 6 else symbol
    url = (f"https://api.twelvedata.com/time_series?symbol={urllib.parse.quote(pair)}"
           f"&interval={interval}&outputsize={min(limit,5000)}&apikey={key}")
    payload = json.loads(_get(url).decode())
    if payload.get("status") == "error":
        raise DataError(str(payload.get("message", "rejected"))[:70])
    rows = payload.get("values") or []
    if not rows:
        raise DataError("empty")
    df = pd.DataFrame([{"time": r["datetime"], "open": float(r["open"]),
                        "high": float(r["high"]), "low": float(r["low"]),
                        "close": float(r["close"])} for r in rows])
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    return df.dropna().sort_values("time").tail(limit).reset_index(drop=True)


def yahoo(ticker: str, interval: str, rng: str, limit: int) -> pd.DataFrame:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(ticker)}?interval={interval}&range={rng}")
    payload = json.loads(_get(url, tries=1).decode())
    res = (payload.get("chart") or {}).get("result")
    if not res:
        raise DataError("no data")
    node = res[0]
    stamps = node.get("timestamp") or []
    q = (node.get("indicators", {}).get("quote") or [{}])[0]
    if not stamps or not q.get("close"):
        raise DataError("empty")
    df = pd.DataFrame({"time": pd.to_datetime(stamps, unit="s", utc=True),
                       "open": q.get("open"), "high": q.get("high"),
                       "low": q.get("low"), "close": q.get("close")}).dropna()
    return df.sort_values("time").tail(limit).reset_index(drop=True)


def demo(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """
    Deterministic price action with real structure — trends, then ranges
    between a floor and ceiling — so every rule has something to find.
    Clearly labelled in the UI. Never presented as live.
    """
    meta = SYMBOLS.get(symbol, {})
    anchor = {"XAUUSD": 4389.2, "EURUSD": 1.1045, "GBPUSD": 1.2918, "USDJPY": 152.40,
              "AUDUSD": 0.6620, "USDCAD": 1.3705, "US30": 44210.0, "NAS100": 20475.0,
              "SPX500": 5740.0, "BTCUSD": 64350.0, "ETHUSD": 2540.0,
              "USOIL": 71.44}.get(symbol, 100.0)
    mins = TIMEFRAMES[timeframe]["minutes"]
    vol = anchor * 0.0008 * math.sqrt(mins / 15)
    rnd = random.Random(sum(map(ord, symbol + timeframe)) * 37)

    regimes, i = [], 0
    while i < limit:
        span = rnd.randint(24, 46)
        kind = "range" if len(regimes) % 2 else rnd.choice(["up", "down"])
        regimes.append((kind, min(span, limit - i)))
        i += span

    rows, p = [], anchor - vol * 12
    floor = ceil = None
    for kind, span in regimes:
        if kind == "range":
            floor, ceil = p - vol * 6.5, p + vol * 6.5
        for _ in range(span):
            o = p
            if kind == "range":
                pos = (p - floor) / max(ceil - floor, 1e-9)
                p += (rnd.random() - 0.5 + (0.5 - pos) * 2.2) * vol
            else:
                p += (rnd.random() - 0.5 + (0.42 if kind == "up" else -0.42)) * vol * 1.4
            body, wick = abs(p - o), vol * (0.25 + rnd.random() * 0.8)
            rows.append({"open": o, "close": p,
                         "high": max(o, p) + wick * rnd.random() + body * 0.1,
                         "low": min(o, p) - wick * rnd.random() - body * 0.1})

    rows = rows[:limit]
    end = pd.Timestamp.now(tz="UTC").floor(f"{mins}min")
    times = [end - pd.Timedelta(minutes=mins * (len(rows) - 1 - i)) for i in range(len(rows))]
    df = pd.DataFrame(rows)
    df.insert(0, "time", times)
    return df


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (df.set_index("time").resample(rule, label="right", closed="right")
              .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
              .dropna().reset_index())


# ── the one call ─────────────────────────────────────────────────────

def fetch(symbol: str, timeframe: str = "M15", limit: int = 400,
          td_key: str = "", allow_demo: bool = True) -> Tuple[pd.DataFrame, str]:
    """
    Returns (candles, origin). Never raises unless allow_demo is False and
    every provider failed.
    """
    meta, tf = SYMBOLS.get(symbol), TIMEFRAMES.get(timeframe)
    if not meta:
        raise DataError(f"{symbol} is not on the watchlist")
    if not tf:
        raise DataError(f"{timeframe} is not a known timeframe")

    key = f"{symbol}_{timeframe}"
    hit = _cache_read(key, tf["ttl"])
    if hit is not None:
        origin = _origin_of(key) or "cache"
        return hit.tail(limit).reset_index(drop=True), origin

    errors = []

    # 1 — Binance: reliable from cloud, covers crypto and a few FX proxies
    if meta.get("binance"):
        try:
            df = binance(meta["binance"], tf["binance"], limit)
            if len(df) >= 60:
                return _store(key, df, limit, "binance")
        except Exception as e:
            errors.append(f"binance {e}")

    # 2 — Twelve Data: everything, if the user supplied a free key
    if td_key:
        try:
            want = limit * (4 if tf.get("resample") else 1)
            df = twelve_data(symbol, td_key, tf["td"], want)
            if tf.get("resample"):
                df = resample(df, tf["resample"])
            if len(df) >= 60:
                return _store(key, df, limit, "twelvedata")
        except Exception as e:
            errors.append(f"twelvedata {e}")

    # 3 — Stooq: daily and above, reachable from cloud
    if tf["minutes"] >= 1440 and meta.get("stooq"):
        try:
            df = stooq(meta["stooq"], limit)
            if len(df) >= 60:
                return _store(key, df, limit, "stooq")
        except Exception as e:
            errors.append(f"stooq {e}")

    # 4 — Yahoo: usually blocked from datacenter IPs, but free when it works
    try:
        iv, rng = tf["yahoo"]
        want = limit * (4 if tf.get("resample") else 1)
        df = yahoo(meta["yahoo"], iv, rng, want)
        if tf.get("resample"):
            df = resample(df, tf["resample"])
        if len(df) >= 60:
            return _store(key, df, limit, "yahoo")
    except Exception as e:
        errors.append(f"yahoo {e}")

    # 5 — any stale copy beats nothing
    old = _cache_read(key, 86_400 * 14)
    if old is not None:
        return old.tail(limit).reset_index(drop=True), "cache"

    if allow_demo:
        return demo(symbol, timeframe, limit), "demo"

    raise DataError(f"{symbol} {timeframe}: " + " · ".join(errors[:3]))


def _store(key: str, df: pd.DataFrame, limit: int, origin: str):
    df = df.tail(limit).reset_index(drop=True)
    _cache_write(key, df)
    try:
        with open(_path(key + "_src"), "w", encoding="utf-8") as f:
            f.write(origin)
    except Exception:
        pass
    return df, origin


def _origin_of(key: str) -> Optional[str]:
    try:
        with open(_path(key + "_src"), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def pips(symbol: str, distance: float) -> float:
    return round(distance / SYMBOLS.get(symbol, {}).get("pip", 0.0001), 1)


def spread_note(origin: str) -> str:
    return {
        "binance": "Binance spot — close to your broker, small basis on metals.",
        "twelvedata": "Twelve Data — exchange prices, matches your broker closely.",
        "stooq": "Stooq daily — end-of-day only, good for levels not entries.",
        "yahoo": "Yahoo — futures quotes; CFD price may differ by a few points.",
        "cache": "Cached — last successful fetch, may be a few minutes old.",
        "demo": "DEMO DATA — generated, not live. Add a free data key to go real.",
    }.get(origin, "")
