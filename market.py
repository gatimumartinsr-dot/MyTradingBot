"""
market.py — free market data, no broker and no API key.

Yahoo Finance covers everything Zonelock scans: gold, FX majors, indices,
crypto and oil. No account, no key.

Yahoo rate-limits bursts hard (HTTP 429), so this module is built around
that: one shared session with a cookie, polite spacing between calls,
exponential backoff on 429, a disk cache that survives Streamlit reruns,
and Stooq as a no-key fallback when Yahoo refuses outright.

    from market import SYMBOLS, TIMEFRAMES, fetch
    df = fetch("XAUUSD", "15m", 400)
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

# ── the watchlist ────────────────────────────────────────────────────

SYMBOLS: Dict[str, Dict] = {
    "XAUUSD":  {"yahoo": "GC=F",     "stooq": "xauusd", "mt5": "XAUUSDm",  "name": "Gold",          "pip": 0.10,   "digits": 2, "class": "Metals"},
    "EURUSD":  {"yahoo": "EURUSD=X", "stooq": "eurusd", "mt5": "EURUSDm",  "name": "Euro",          "pip": 0.0001, "digits": 5, "class": "FX majors"},
    "GBPUSD":  {"yahoo": "GBPUSD=X", "stooq": "gbpusd", "mt5": "GBPUSDm",  "name": "Pound",         "pip": 0.0001, "digits": 5, "class": "FX majors"},
    "USDJPY":  {"yahoo": "USDJPY=X", "stooq": "usdjpy", "mt5": "USDJPYm",  "name": "Dollar-Yen",    "pip": 0.01,   "digits": 3, "class": "FX majors"},
    "AUDUSD":  {"yahoo": "AUDUSD=X", "stooq": "audusd", "mt5": "AUDUSDm",  "name": "Aussie",        "pip": 0.0001, "digits": 5, "class": "FX majors"},
    "USDCAD":  {"yahoo": "USDCAD=X", "stooq": "usdcad", "mt5": "USDCADm",  "name": "Dollar-Loonie", "pip": 0.0001, "digits": 5, "class": "FX majors"},
    "US30":    {"yahoo": "YM=F",     "stooq": "^dji",   "mt5": "US30m",    "name": "Dow 30",        "pip": 1.0,    "digits": 1, "class": "Indices"},
    "NAS100":  {"yahoo": "NQ=F",     "stooq": "^ndq",   "mt5": "NAS100m",  "name": "Nasdaq 100",    "pip": 1.0,    "digits": 1, "class": "Indices"},
    "SPX500":  {"yahoo": "ES=F",     "stooq": "^spx",   "mt5": "US500m",   "name": "S&P 500",       "pip": 0.25,   "digits": 2, "class": "Indices"},
    "BTCUSD":  {"yahoo": "BTC-USD",  "stooq": "",       "mt5": "BTCUSDm",  "name": "Bitcoin",       "pip": 1.0,    "digits": 1, "class": "Crypto"},
    "ETHUSD":  {"yahoo": "ETH-USD",  "stooq": "",       "mt5": "ETHUSDm",  "name": "Ethereum",      "pip": 0.1,    "digits": 2, "class": "Crypto"},
    "USOIL":   {"yahoo": "CL=F",     "stooq": "cl.f",   "mt5": "USOILm",   "name": "WTI Crude",     "pip": 0.01,   "digits": 2, "class": "Energy"},
}

# ── timeframes ───────────────────────────────────────────────────────
# label · yahoo interval · yahoo range · minutes · cache seconds

TIMEFRAMES: Dict[str, Dict] = {
    "M5":  {"yahoo": "5m",  "range": "5d",  "minutes": 5,    "ttl": 180,  "label": "5 minute"},
    "M15": {"yahoo": "15m", "range": "1mo", "minutes": 15,   "ttl": 300,  "label": "15 minute"},
    "M30": {"yahoo": "30m", "range": "1mo", "minutes": 30,   "ttl": 600,  "label": "30 minute"},
    "H1":  {"yahoo": "1h",  "range": "3mo", "minutes": 60,   "ttl": 900,  "label": "1 hour"},
    "H4":  {"yahoo": "1h",  "range": "6mo", "minutes": 240,  "ttl": 1800, "label": "4 hour", "resample": "4h"},
    "D1":  {"yahoo": "1d",  "range": "2y",  "minutes": 1440, "ttl": 3600, "label": "Daily"},
    "W1":  {"yahoo": "1wk", "range": "5y",  "minutes": 10080, "ttl": 7200, "label": "Weekly"},
}

# Which timeframes a multi-timeframe read consults, fastest to slowest.
MTF_LADDER = ["M15", "H1", "H4", "D1"]

CACHE_DIR = os.environ.get("ZONELOCK_CACHE", ".zlcache")
MIN_GAP = 1.1          # seconds between outbound Yahoo calls
_lock = threading.Lock()
_last_call = [0.0]
_cookie: List[str] = [""]


class DataError(RuntimeError):
    pass


# ── polite HTTP ──────────────────────────────────────────────────────

def _throttle() -> None:
    with _lock:
        wait = MIN_GAP - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()


def _open(url: str, timeout: int = 14) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    if _cookie[0]:
        headers["Cookie"] = _cookie[0]
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        setc = r.headers.get("Set-Cookie")
        if setc and not _cookie[0]:
            _cookie[0] = setc.split(";")[0]
        return r.read()


def _get(url: str, tries: int = 4) -> bytes:
    """GET with spacing and exponential backoff on 429 / 5xx."""
    delay = 1.6
    for attempt in range(tries):
        _throttle()
        try:
            return _open(url)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < tries - 1:
                time.sleep(delay + random.random() * 0.7)
                delay *= 2.1
                continue
            raise DataError(f"HTTP {e.code}") from None
        except Exception as e:
            if attempt < tries - 1:
                time.sleep(delay)
                delay *= 1.8
                continue
            raise DataError(str(e)) from None
    raise DataError("exhausted retries")


# ── disk cache (survives Streamlit reruns and reboots) ───────────────

def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in key)
    return os.path.join(CACHE_DIR, f"{safe}.json")


def _cache_read(key: str, ttl: int) -> Optional[pd.DataFrame]:
    path = _cache_path(key)
    try:
        if time.time() - os.path.getmtime(path) > ttl:
            return None
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        df = pd.DataFrame(payload)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df if len(df) >= 40 else None
    except Exception:
        return None


def _cache_write(key: str, df: pd.DataFrame) -> None:
    try:
        out = df.copy()
        out["time"] = out["time"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump(out.to_dict("records"), f)
    except Exception:
        pass


def _cache_stale(key: str) -> Optional[pd.DataFrame]:
    """Last good copy at any age — better than an error message."""
    return _cache_read(key, ttl=86_400 * 7)


# ── Yahoo ────────────────────────────────────────────────────────────

def yahoo(ticker: str, interval: str, rng: str, limit: int) -> pd.DataFrame:
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(ticker)}?interval={interval}&range={rng}"
           f"&includePrePost=false")
    payload = json.loads(_get(url).decode())

    result = (payload.get("chart") or {}).get("result")
    if not result:
        err = ((payload.get("chart") or {}).get("error") or {}).get("description", "no data")
        raise DataError(err)

    node = result[0]
    stamps = node.get("timestamp") or []
    q = (node.get("indicators", {}).get("quote") or [{}])[0]
    if not stamps or not q.get("close"):
        raise DataError("empty series")

    df = pd.DataFrame({
        "time": pd.to_datetime(stamps, unit="s", utc=True),
        "open": q.get("open"), "high": q.get("high"),
        "low": q.get("low"), "close": q.get("close"),
    }).dropna()
    return df.drop_duplicates("time").sort_values("time").tail(limit).reset_index(drop=True)


# ── Stooq (no key, daily only, good as a last resort) ────────────────

def stooq(code: str, limit: int) -> pd.DataFrame:
    if not code:
        raise DataError("no Stooq mapping")
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(code)}&i=d"
    text = _get(url).decode()
    lines = [l for l in text.strip().splitlines() if l and not l.startswith("<")]
    if len(lines) < 5:
        raise DataError("stooq empty")

    rows = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            rows.append({"time": parts[0], "open": float(parts[1]), "high": float(parts[2]),
                         "low": float(parts[3]), "close": float(parts[4])})
        except ValueError:
            continue
    if not rows:
        raise DataError("stooq unparseable")

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    return df.dropna().sort_values("time").tail(limit).reset_index(drop=True)


# ── Twelve Data (optional free key) ──────────────────────────────────

TD_INTERVAL = {"5m": "5min", "15m": "15min", "30m": "30min",
               "1h": "1h", "1d": "1day", "1wk": "1week"}


def twelve_data(symbol: str, api_key: str, interval: str, limit: int) -> pd.DataFrame:
    pair = symbol[:3] + "/" + symbol[3:] if len(symbol) == 6 else symbol
    url = (f"https://api.twelvedata.com/time_series?symbol={urllib.parse.quote(pair)}"
           f"&interval={TD_INTERVAL.get(interval,'15min')}&outputsize={min(limit,5000)}"
           f"&apikey={api_key}")
    payload = json.loads(_get(url, tries=2).decode())
    if payload.get("status") == "error":
        raise DataError(payload.get("message", "rejected"))
    rows = payload.get("values") or []
    if not rows:
        raise DataError("empty")
    df = pd.DataFrame([{"time": r["datetime"], "open": float(r["open"]),
                        "high": float(r["high"]), "low": float(r["low"]),
                        "close": float(r["close"])} for r in rows])
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    return df.dropna().sort_values("time").tail(limit).reset_index(drop=True)


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = (df.set_index("time")
             .resample(rule, label="right", closed="right")
             .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
             .dropna().reset_index())
    return out


# ── the one call the app makes ───────────────────────────────────────

def fetch(symbol: str, timeframe: str = "M15", limit: int = 400,
          td_key: str = "", allow_stale: bool = True) -> pd.DataFrame:
    """
    Candles for a watchlist symbol at a named timeframe.
    Disk cache → Yahoo → Twelve Data → Stooq → stale cache.
    """
    meta = SYMBOLS.get(symbol)
    tf = TIMEFRAMES.get(timeframe)
    if not meta:
        raise DataError(f"{symbol} is not on the watchlist")
    if not tf:
        raise DataError(f"{timeframe} is not a known timeframe")

    key = f"{symbol}_{timeframe}"
    hit = _cache_read(key, tf["ttl"])
    if hit is not None:
        return hit.tail(limit).reset_index(drop=True)

    want = limit * (4 if tf.get("resample") else 1)
    errors = []

    try:
        df = yahoo(meta["yahoo"], tf["yahoo"], tf["range"], want)
        if tf.get("resample"):
            df = resample(df, tf["resample"])
        if len(df) >= 60:
            df = df.tail(limit).reset_index(drop=True)
            _cache_write(key, df)
            return df
        errors.append(f"Yahoo returned {len(df)} bars")
    except Exception as e:
        errors.append(f"Yahoo {e}")

    if td_key:
        try:
            df = twelve_data(symbol, td_key, tf["yahoo"], want)
            if tf.get("resample"):
                df = resample(df, tf["resample"])
            if len(df) >= 60:
                df = df.tail(limit).reset_index(drop=True)
                _cache_write(key, df)
                return df
        except Exception as e:
            errors.append(f"TwelveData {e}")

    if tf["minutes"] >= 1440 and meta.get("stooq"):
        try:
            df = stooq(meta["stooq"], limit)
            if len(df) >= 60:
                _cache_write(key, df)
                return df
        except Exception as e:
            errors.append(f"Stooq {e}")

    if allow_stale:
        old = _cache_stale(key)
        if old is not None:
            return old.tail(limit).reset_index(drop=True)

    raise DataError(f"{symbol} {timeframe}: " + " · ".join(errors))


def cache_age(symbol: str, timeframe: str) -> Optional[int]:
    """Seconds since this series was last refreshed, or None."""
    try:
        return int(time.time() - os.path.getmtime(_cache_path(f"{symbol}_{timeframe}")))
    except Exception:
        return None


def warm(symbols: List[str], timeframes: List[str], td_key: str = "",
         progress=None) -> Dict[str, str]:
    """Pre-fetch a grid of series, spacing requests. Returns symbol → error."""
    failed: Dict[str, str] = {}
    jobs = [(s, t) for s in symbols for t in timeframes]
    for i, (sym, tf) in enumerate(jobs, 1):
        if progress:
            progress(i / len(jobs), f"{sym} · {tf}")
        try:
            fetch(sym, tf, 400, td_key)
        except Exception as exc:
            failed[f"{sym} {tf}"] = str(exc)
    return failed


def pips(symbol: str, distance: float) -> float:
    return round(distance / SYMBOLS.get(symbol, {}).get("pip", 0.0001), 1)
