"""
market.py — free market data, no broker and no API key.

Yahoo Finance covers everything Zonelock scans: gold, FX majors, indices,
crypto and oil. No account, no key, no rate limit worth worrying about.
Twelve Data is the fallback if Yahoo is blocked (free tier, 800 calls/day).

    from market import SYMBOLS, fetch
    df = fetch("XAUUSD", "15m", 400)

Every symbol carries the name you place it under on MT5, so the setup card
can tell you exactly what to type into the terminal.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

# ── the watchlist ────────────────────────────────────────────────────
# yahoo: Yahoo Finance ticker · mt5: what you type into MetaTrader
# pip: one pip in price terms · digits: display precision

SYMBOLS: Dict[str, Dict] = {
    "XAUUSD":  {"yahoo": "GC=F",     "mt5": "XAUUSDm",  "name": "Gold",          "pip": 0.10,    "digits": 2, "class": "Metals"},
    "EURUSD":  {"yahoo": "EURUSD=X", "mt5": "EURUSDm",  "name": "Euro",          "pip": 0.0001,  "digits": 5, "class": "FX majors"},
    "GBPUSD":  {"yahoo": "GBPUSD=X", "mt5": "GBPUSDm",  "name": "Pound",         "pip": 0.0001,  "digits": 5, "class": "FX majors"},
    "USDJPY":  {"yahoo": "USDJPY=X", "mt5": "USDJPYm",  "name": "Dollar-Yen",    "pip": 0.01,    "digits": 3, "class": "FX majors"},
    "AUDUSD":  {"yahoo": "AUDUSD=X", "mt5": "AUDUSDm",  "name": "Aussie",        "pip": 0.0001,  "digits": 5, "class": "FX majors"},
    "USDCAD":  {"yahoo": "USDCAD=X", "mt5": "USDCADm",  "name": "Dollar-Loonie", "pip": 0.0001,  "digits": 5, "class": "FX majors"},
    "US30":    {"yahoo": "YM=F",     "mt5": "US30m",    "name": "Dow 30",        "pip": 1.0,     "digits": 1, "class": "Indices"},
    "NAS100":  {"yahoo": "NQ=F",     "mt5": "NAS100m",  "name": "Nasdaq 100",    "pip": 1.0,     "digits": 1, "class": "Indices"},
    "SPX500":  {"yahoo": "ES=F",     "mt5": "US500m",   "name": "S&P 500",       "pip": 0.25,    "digits": 2, "class": "Indices"},
    "BTCUSD":  {"yahoo": "BTC-USD",  "mt5": "BTCUSDm",  "name": "Bitcoin",       "pip": 1.0,     "digits": 1, "class": "Crypto"},
    "ETHUSD":  {"yahoo": "ETH-USD",  "mt5": "ETHUSDm",  "name": "Ethereum",      "pip": 0.1,     "digits": 2, "class": "Crypto"},
    "USOIL":   {"yahoo": "CL=F",     "mt5": "USOILm",   "name": "WTI Crude",     "pip": 0.01,    "digits": 2, "class": "Energy"},
}

# Yahoo's chart API: interval → the longest range it will serve
RANGE_FOR = {"5m": "5d", "15m": "1mo", "30m": "1mo",
             "60m": "3mo", "1h": "3mo", "1d": "2y"}


class DataError(RuntimeError):
    pass


def _get(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ── Yahoo Finance ────────────────────────────────────────────────────

def yahoo(ticker: str, interval: str = "15m", limit: int = 400) -> pd.DataFrame:
    rng = RANGE_FOR.get(interval, "1mo")
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(ticker)}?interval={interval}&range={rng}")
    payload = json.loads(_get(url).decode())

    result = (payload.get("chart") or {}).get("result")
    if not result:
        err = ((payload.get("chart") or {}).get("error") or {}).get("description", "no data")
        raise DataError(f"Yahoo: {err}")

    node = result[0]
    stamps = node.get("timestamp") or []
    q = (node.get("indicators", {}).get("quote") or [{}])[0]
    if not stamps or not q.get("close"):
        raise DataError("Yahoo returned an empty series.")

    df = pd.DataFrame({
        "time": pd.to_datetime(stamps, unit="s", utc=True),
        "open": q.get("open"), "high": q.get("high"),
        "low": q.get("low"), "close": q.get("close"),
    }).dropna()

    return df.drop_duplicates("time").sort_values("time").tail(limit).reset_index(drop=True)


# ── Twelve Data (fallback, free key) ─────────────────────────────────

TD_INTERVAL = {"5m": "5min", "15m": "15min", "30m": "30min",
               "60m": "1h", "1h": "1h", "1d": "1day"}


def twelve_data(symbol: str, api_key: str, interval: str = "15m",
                limit: int = 400) -> pd.DataFrame:
    pair = symbol[:3] + "/" + symbol[3:] if len(symbol) == 6 else symbol
    url = (f"https://api.twelvedata.com/time_series?symbol={urllib.parse.quote(pair)}"
           f"&interval={TD_INTERVAL.get(interval,'15min')}&outputsize={min(limit,5000)}"
           f"&apikey={api_key}")
    payload = json.loads(_get(url).decode())
    if payload.get("status") == "error":
        raise DataError(f"Twelve Data: {payload.get('message','rejected')}")

    rows = payload.get("values") or []
    if not rows:
        raise DataError("Twelve Data returned nothing.")

    df = pd.DataFrame([{
        "time": r["datetime"], "open": float(r["open"]), "high": float(r["high"]),
        "low": float(r["low"]), "close": float(r["close"]),
    } for r in rows])
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    return df.dropna().sort_values("time").tail(limit).reset_index(drop=True)


# ── the one call the app makes ───────────────────────────────────────

def fetch(symbol: str, interval: str = "15m", limit: int = 400,
          td_key: str = "") -> pd.DataFrame:
    """Candles for a watchlist symbol. Yahoo first, Twelve Data if it fails."""
    meta = SYMBOLS.get(symbol)
    if not meta:
        raise DataError(f"{symbol} is not on the watchlist.")

    try:
        df = yahoo(meta["yahoo"], interval, limit)
        if len(df) >= 60:
            return df
    except Exception as first:
        if not td_key:
            raise DataError(f"{symbol}: {first}") from None
        try:
            return twelve_data(symbol, td_key, interval, limit)
        except Exception as second:
            raise DataError(f"{symbol}: Yahoo {first} · Twelve Data {second}") from None
    raise DataError(f"{symbol}: not enough candles returned.")


def spot(symbol: str) -> Optional[float]:
    meta = SYMBOLS.get(symbol)
    if not meta:
        return None
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
               f"{urllib.parse.quote(meta['yahoo'])}?interval=1m&range=1d")
        node = json.loads(_get(url).decode())["chart"]["result"][0]
        return float(node["meta"]["regularMarketPrice"])
    except Exception:
        return None


def pips(symbol: str, distance: float) -> float:
    meta = SYMBOLS.get(symbol, {})
    return round(distance / meta.get("pip", 0.0001), 1)
