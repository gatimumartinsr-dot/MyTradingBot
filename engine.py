"""
engine.py — the loop that actually trades.

Connects to the MT5 terminal, pulls candles, asks strategy.evaluate() for a
decision, places the order if it passes, and writes EVERY decision — taken or
rejected — to the journal the app reads.

Run it as a service:  python engine.py
Windows only: the MetaTrader5 package binds to a running terminal.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

from strategy import Rules, Decision, evaluate

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

JOURNAL = os.environ.get("ZONELOCK_JOURNAL", "journal.jsonl")
POLL_SECONDS = int(os.environ.get("ZONELOCK_POLL", "20"))
MAGIC = 20260910

SYMBOLS = os.environ.get("ZONELOCK_SYMBOLS", "XAUUSDm,EURUSDm,GBPUSDm,US30m,NAS100m,BTCUSDm,USOILm").split(",")
TIMEFRAME = "M15"


# ──────────────────────────────────────────────────────────────────────
# Terminal
# ──────────────────────────────────────────────────────────────────────

def connect(login: int, password: str, server: str) -> tuple[bool, str]:
    if not MT5_AVAILABLE:
        return False, "MetaTrader5 package unavailable — this host is not Windows."
    if not mt5.initialize():
        return False, f"Terminal did not initialise: {mt5.last_error()}"
    if not mt5.login(login=int(login), password=password, server=server):
        err = mt5.last_error()
        mt5.shutdown()
        return False, f"Login rejected: {err}"
    info = mt5.account_info()
    return True, f"Bound to {server} · {info.login} · balance {info.balance:.2f} {info.currency}"


def candles(symbol: str, count: int = 300) -> Optional[pd.DataFrame]:
    tf = getattr(mt5, f"TIMEFRAME_{TIMEFRAME}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    # drop the still-forming bar: rules only ever judge CLOSED candles
    return df.iloc[:-1].reset_index(drop=True)


def symbol_costs(symbol: str) -> tuple[float, float]:
    info = mt5.symbol_info(symbol)
    if info is None:
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
    if info is None:
        return 1.0, 0.00001
    return float(info.trade_tick_value), float(info.trade_tick_size)


def open_count() -> int:
    positions = mt5.positions_get()
    return 0 if positions is None else len([p for p in positions if p.magic == MAGIC])


def realised_today() -> float:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(start, datetime.now(timezone.utc))
    if not deals:
        return 0.0
    return round(sum(d.profit for d in deals if d.magic == MAGIC), 2)


def place(decision: Decision) -> tuple[bool, str]:
    tick = mt5.symbol_info_tick(decision.symbol)
    if tick is None:
        return False, "No tick data."
    is_buy = decision.direction == "BUY"
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": decision.symbol,
        "volume": float(decision.lots),
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": tick.ask if is_buy else tick.bid,
        "sl": float(decision.stop_loss),
        "tp": float(decision.take_profit),
        "deviation": 20,
        "magic": MAGIC,
        "comment": "Zonelock",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Refused: {getattr(result, 'comment', 'no response')}"
    return True, f"Ticket {result.order}"


# ──────────────────────────────────────────────────────────────────────
# Journal — one JSON object per line, taken and rejected alike
# ──────────────────────────────────────────────────────────────────────

def log(decision: Decision, outcome: str = "") -> None:
    row = decision.to_dict()
    row["outcome"] = outcome
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def read_journal(limit: int = 200) -> List[Dict]:
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows[-limit:][::-1]


# ──────────────────────────────────────────────────────────────────────
# News — plug your calendar here
# ──────────────────────────────────────────────────────────────────────

_NEWS_CACHE: Dict[str, object] = {"at": None, "rows": []}


def fetch_news() -> List[Dict]:
    """
    This week's economic calendar from Forex Factory's public JSON (no key).
    Cached 15 minutes. Fails CLOSED: if the feed is unreachable we return a
    sentinel far-future block so the engine stops opening trades rather than
    trading blind into a release.
    """
    import urllib.request

    now = datetime.now(timezone.utc)
    last = _NEWS_CACHE["at"]
    if last and (now - last).total_seconds() < 900:
        return _NEWS_CACHE["rows"]

    try:
        req = urllib.request.Request(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0 (Zonelock)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"! calendar unreachable ({exc}) — holding entries")
        return [{"time": now, "impact": "high", "currency": "USD",
                 "title": "calendar unreachable"}]

    rows: List[Dict] = []
    for ev in data:
        try:
            when = pd.to_datetime(ev.get("date")).tz_convert("UTC").to_pydatetime()
        except Exception:
            continue
        rows.append({"time": when,
                     "impact": (ev.get("impact") or "").lower(),
                     "currency": (ev.get("country") or "").upper(),
                     "title": ev.get("title", "")})

    _NEWS_CACHE.update(at=now, rows=rows)
    return rows


# ──────────────────────────────────────────────────────────────────────
# Loop
# ──────────────────────────────────────────────────────────────────────

def tick(rules: Rules, live: bool) -> None:
    account = mt5.account_info()
    if account is None:
        print("No account info — terminal disconnected.")
        return

    balance = float(account.balance)
    positions = open_count()
    pnl = realised_today()
    news = fetch_news()
    now = datetime.now(timezone.utc)

    for symbol in SYMBOLS:
        symbol = symbol.strip()
        df = candles(symbol)
        if df is None:
            continue
        tick_value, tick_size = symbol_costs(symbol)

        decision = evaluate(
            symbol, df, balance=balance, tick_value=tick_value, tick_size=tick_size,
            open_positions=positions, daily_pnl=pnl, news_events=news,
            now_utc=now, rules=rules,
        )

        if not decision.taken:
            log(decision)
            print(f"· {symbol}: skipped — {decision.verdict}")
            continue

        if not live:
            log(decision, outcome="demo — not sent")
            print(f"◆ {symbol}: DEMO {decision.direction} {decision.lots} @ {decision.entry}")
            continue

        ok, note = place(decision)
        log(decision, outcome=note)
        positions += 1 if ok else 0
        print(f"{'✓' if ok else '✕'} {symbol}: {decision.direction} {decision.lots} — {note}")


def main() -> None:
    login = int(os.environ["MT5_LOGIN"])
    password = os.environ["MT5_PASSWORD"]
    server = os.environ["MT5_SERVER"]
    live = os.environ.get("ZONELOCK_MODE", "demo").lower() == "live"

    ok, note = connect(login, password, server)
    print(note)
    if not ok:
        raise SystemExit(1)

    rules = Rules()
    print(f"Zonelock running in {'LIVE' if live else 'DEMO'} mode on {len(SYMBOLS)} symbols.")
    try:
        while True:
            try:
                tick(rules, live)
            except Exception as exc:  # never let one bad bar kill the service
                print(f"! cycle error: {exc}")
            time.sleep(POLL_SECONDS)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
