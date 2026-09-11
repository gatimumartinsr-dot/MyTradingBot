"""
scanner.py — headless Zonelock scan, for a scheduler.

Runs the same rules as the app and pushes anything it finds to Telegram, so
alerts reach you while the app is closed. No broker, no browser.

    export TELEGRAM_TOKEN=... TELEGRAM_CHAT=...
    python scanner.py

Free schedulers that run this every 15 minutes: GitHub Actions (cron),
PythonAnywhere, Railway, Render cron jobs.
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from market import SYMBOLS, fetch, pips
from strategy import Rules, atr, confluence, daily_zones, evaluate, grade

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT", "")
ACCOUNT = float(os.environ.get("ZONELOCK_ACCOUNT", "1000"))
MIN_GRADE = os.environ.get("ZONELOCK_MIN_GRADE", "B").upper()
PICKS = os.environ.get("ZONELOCK_PICKS", "picks.jsonl")
SEEN = os.environ.get("ZONELOCK_SEEN", "seen.json")

RANK = {"A": 0, "B": 1, "C": 2, "—": 3}


def send(text: str) -> bool:
    if not (TOKEN and CHAT):
        print(text)
        return False
    url = (f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT}"
           f"&parse_mode=HTML&text={urllib.parse.quote(text)}")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except Exception as exc:
        print(f"! telegram: {exc}")
        return False


def load_seen() -> dict:
    try:
        with open(SEEN, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_seen(seen: dict) -> None:
    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(seen, f)


def main() -> None:
    rules = Rules()
    seen = load_seen()
    now = datetime.now(timezone.utc)
    sent = 0

    for symbol in SYMBOLS:
        try:
            m15 = fetch(symbol, "15m", 400)
            try:
                d1 = fetch(symbol, "1d", 120)
            except Exception:
                d1 = None
        except Exception as exc:
            print(f"· {symbol}: {exc}")
            continue

        price = float(m15["close"].iloc[-1])
        dec = evaluate(symbol, m15, balance=ACCOUNT, tick_value=1.0,
                       tick_size=SYMBOLS[symbol]["pip"], rules=rules)

        if not dec.taken:
            print(f"· {symbol}: {dec.verdict}")
            continue

        levels = daily_zones(d1, price) if d1 is not None else []
        conf = confluence(dec, levels, atr(m15, 14))
        g = grade(dec, conf)
        if RANK[g] > RANK.get(MIN_GRADE, 1):
            print(f"· {symbol}: {g}-grade, below {MIN_GRADE}")
            continue

        # one alert per setup per candle
        key = f"{symbol}:{dec.direction}:{round(dec.entry, 4)}"
        if seen.get(key) == m15['time'].iloc[-1].isoformat():
            continue
        seen[key] = m15['time'].iloc[-1].isoformat()

        meta = SYMBOLS[symbol]
        dig = meta["digits"]
        risk = pips(symbol, abs(dec.entry - dec.stop_loss))
        body = (f"<b>{g}-grade · {meta['mt5']} {dec.direction}</b>\n"
                f"Entry <code>{dec.entry:,.{dig}f}</code>\n"
                f"SL <code>{dec.stop_loss:,.{dig}f}</code> ({risk:g} pips)\n"
                f"TP <code>{dec.take_profit:,.{dig}f}</code>\n"
                f"{dec.lots:.2f} lots · {dec.rr}R\n\n{dec.headline}")
        if conf:
            body += f"\n\nDaily confluence: {', '.join(conf)}"

        if send(body):
            sent += 1
        with open(PICKS, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "at": now.isoformat(), "symbol": symbol, "mt5": meta["mt5"], "grade": g,
                "direction": dec.direction, "entry": dec.entry, "sl": dec.stop_loss,
                "tp": dec.take_profit, "rr": dec.rr, "lots": dec.lots,
                "headline": dec.headline, "tags": dec.tags, "confluence": conf,
                "outcome": "pending"}) + "\n")
        print(f"✓ {symbol}: {g}-grade {dec.direction} alert sent")

    save_seen(seen)
    print(f"{now:%H:%M} UTC — {sent} alerts sent.")


if __name__ == "__main__":
    main()
