"""
strategy.py — Zonelock rule engine.

Pure functions over an OHLC DataFrame. No MT5 import, no network, no globals:
you can unit-test every rule with a CSV. `evaluate()` is the entry point and
always returns a Decision — either a signal to place, or a rejection carrying
the exact rule that stopped it, which is what the app's journal renders.

DataFrame contract: columns time, open, high, low, close (oldest row first).
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Tuple

import pandas as pd


# ──────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Rules:
    # structure
    swing_lookback: int = 3           # bars each side that define a swing point
    zone_atr_mult: float = 0.35       # zone thickness as a multiple of ATR
    zone_touch_tolerance: float = 0.5 # how close price must be, in zone-heights
    min_zone_touches: int = 2         # a level needs this many touches to count

    # confirmation
    require_reversal_candle: bool = True
    allowed_patterns: Tuple[str, ...] = ("engulfing", "pin", "star")
    min_body_ratio: float = 0.5       # engulfing body vs. prior body

    # smart-money
    require_fvg_unfilled: bool = True
    min_fvg_atr: float = 0.15         # ignore gaps smaller than this
    require_ob_structure: bool = True # order block must carry BOS or CHoCH
    accept_choch: bool = True

    # risk
    base_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 5.0
    risk_percent: float = 2.0
    min_rr: float = 1.5
    max_open_positions: int = 3
    daily_profit_cap: float = 50.0
    max_daily_loss: float = 25.0

    # timing
    news_block_minutes: int = 30
    session_filter: bool = True
    min_atr_percentile: float = 0.25  # skip dead volatility


# ──────────────────────────────────────────────────────────────────────
# Results
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Check:
    label: str
    value: str
    passed: bool


@dataclass
class Decision:
    symbol: str
    taken: bool
    direction: Optional[str] = None      # "BUY" | "SELL"
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    lots: float = 0.0
    rr: Optional[float] = None
    headline: str = ""
    verdict: str = ""                    # short rejection reason for the journal
    tags: List[str] = field(default_factory=list)
    checks: List[Check] = field(default_factory=list)
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["checks"] = [asdict(c) for c in self.checks]
        return d


# ──────────────────────────────────────────────────────────────────────
# Indicators
# ──────────────────────────────────────────────────────────────────────

def atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["high"], df["low"], df["close"]
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def swing_points(df: pd.DataFrame, lookback: int) -> Tuple[List[int], List[int]]:
    """Indices of confirmed swing highs and swing lows."""
    highs, lows = [], []
    h, l = df["high"].values, df["low"].values
    for i in range(lookback, len(df) - lookback):
        window_h = h[i - lookback:i + lookback + 1]
        window_l = l[i - lookback:i + lookback + 1]
        if h[i] == window_h.max() and (window_h == h[i]).sum() == 1:
            highs.append(i)
        if l[i] == window_l.min() and (window_l == l[i]).sum() == 1:
            lows.append(i)
    return highs, lows


# ──────────────────────────────────────────────────────────────────────
# Support & resistance
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Zone:
    kind: str      # "support" | "resistance"
    low: float
    high: float
    touches: int

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2

    def contains(self, price: float, tolerance: float = 0.0) -> bool:
        pad = (self.high - self.low) * tolerance
        return (self.low - pad) <= price <= (self.high + pad)


def build_zones(df: pd.DataFrame, rules: Rules) -> List[Zone]:
    """Cluster swing points into zones. Levels touched more often come first."""
    a = atr(df, 14)
    if not a or a != a:
        return []
    thickness = a * rules.zone_atr_mult
    highs, lows = swing_points(df, rules.swing_lookback)

    def cluster(indices, col, kind) -> List[Zone]:
        levels = sorted(df[col].values[i] for i in indices)
        out, group = [], []
        for lv in levels:
            if group and lv - group[0] > thickness:
                out.append(Zone(kind, min(group), max(group) + thickness * 0.4, len(group)))
                group = []
            group.append(lv)
        if group:
            out.append(Zone(kind, min(group), max(group) + thickness * 0.4, len(group)))
        return [z for z in out if z.touches >= rules.min_zone_touches]

    return cluster(lows, "low", "support") + cluster(highs, "high", "resistance")


def nearest_zone(zones: List[Zone], price: float, kind: str) -> Optional[Zone]:
    candidates = [z for z in zones if z.kind == kind]
    if not candidates:
        return None
    return min(candidates, key=lambda z: abs(z.mid - price))


# ──────────────────────────────────────────────────────────────────────
# Reversal candles
# ──────────────────────────────────────────────────────────────────────

def reversal_candle(df: pd.DataFrame, direction: str, rules: Rules) -> Optional[str]:
    """Name of the confirming pattern on the last CLOSED bar, or None."""
    if len(df) < 3:
        return None
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

    def body(c):
        return abs(c["close"] - c["open"])

    def bull(c):
        return c["close"] > c["open"]

    rng = c3["high"] - c3["low"]
    if rng <= 0:
        return None

    if "engulfing" in rules.allowed_patterns:
        if direction == "BUY" and bull(c3) and not bull(c2) \
                and c3["close"] >= c2["open"] and c3["open"] <= c2["close"] \
                and body(c3) >= body(c2) * rules.min_body_ratio:
            return "bullish engulfing"
        if direction == "SELL" and not bull(c3) and bull(c2) \
                and c3["close"] <= c2["open"] and c3["open"] >= c2["close"] \
                and body(c3) >= body(c2) * rules.min_body_ratio:
            return "bearish engulfing"

    if "pin" in rules.allowed_patterns:
        lower = min(c3["open"], c3["close"]) - c3["low"]
        upper = c3["high"] - max(c3["open"], c3["close"])
        if direction == "BUY" and lower > rng * 0.6 and body(c3) < rng * 0.35:
            return "bullish pin bar"
        if direction == "SELL" and upper > rng * 0.6 and body(c3) < rng * 0.35:
            return "bearish pin bar"

    if "star" in rules.allowed_patterns:
        small = body(c2) < body(c1) * 0.5
        if direction == "BUY" and not bull(c1) and small and bull(c3) \
                and c3["close"] > (c1["open"] + c1["close"]) / 2:
            return "morning star"
        if direction == "SELL" and bull(c1) and small and not bull(c3) \
                and c3["close"] < (c1["open"] + c1["close"]) / 2:
            return "evening star"

    return None


# ──────────────────────────────────────────────────────────────────────
# Fair value gaps
# ──────────────────────────────────────────────────────────────────────

@dataclass
class FVG:
    direction: str   # "bullish" | "bearish"
    low: float
    high: float
    index: int
    filled: bool

    @property
    def size(self) -> float:
        return self.high - self.low


def find_fvgs(df: pd.DataFrame, rules: Rules) -> List[FVG]:
    """Three-candle imbalance: candle 1 and candle 3 do not overlap."""
    a = atr(df, 14)
    out: List[FVG] = []
    if not a or a != a:
        return out
    floor = a * rules.min_fvg_atr

    for i in range(2, len(df)):
        c1, c3 = df.iloc[i - 2], df.iloc[i]
        if c3["low"] > c1["high"] and c3["low"] - c1["high"] >= floor:
            gap = FVG("bullish", c1["high"], c3["low"], i, False)
        elif c1["low"] > c3["high"] and c1["low"] - c3["high"] >= floor:
            gap = FVG("bearish", c3["high"], c1["low"], i, False)
        else:
            continue
        later = df.iloc[i + 1:]
        if len(later):
            gap.filled = bool(((later["low"] <= gap.high) & (later["high"] >= gap.low)).any())
        out.append(gap)
    return out


# ──────────────────────────────────────────────────────────────────────
# Market structure: BOS / CHoCH, and the order blocks they create
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Structure:
    event: str        # "BOS" | "CHoCH" | "none"
    direction: str    # "bullish" | "bearish" | "none"
    broke_index: Optional[int] = None
    level: Optional[float] = None


def market_structure(df: pd.DataFrame, rules: Rules) -> Structure:
    highs, lows = swing_points(df, rules.swing_lookback)
    if len(highs) < 2 or len(lows) < 2:
        return Structure("none", "none")

    hi_vals = [df["high"].values[i] for i in highs]
    lo_vals = [df["low"].values[i] for i in lows]
    trend = "bullish" if (hi_vals[-1] > hi_vals[-2] and lo_vals[-1] > lo_vals[-2]) else \
            "bearish" if (hi_vals[-1] < hi_vals[-2] and lo_vals[-1] < lo_vals[-2]) else "range"

    last_close = float(df["close"].iloc[-1])
    last_high, last_low = hi_vals[-1], lo_vals[-1]

    if last_close > last_high:
        event = "BOS" if trend == "bullish" else "CHoCH"
        return Structure(event, "bullish", highs[-1], last_high)
    if last_close < last_low:
        event = "BOS" if trend == "bearish" else "CHoCH"
        return Structure(event, "bearish", lows[-1], last_low)
    return Structure("none", trend)


@dataclass
class OrderBlock:
    direction: str   # "bullish" | "bearish"
    low: float
    high: float
    index: int
    event: str       # the BOS / CHoCH that validated it


def order_blocks(df: pd.DataFrame, rules: Rules) -> List[OrderBlock]:
    """The last opposite-colour candle before the impulse that broke structure."""
    st = market_structure(df, rules)
    if st.event == "none" or st.broke_index is None:
        return []
    if st.event == "CHoCH" and not rules.accept_choch:
        return []

    out: List[OrderBlock] = []
    want_bull = st.direction == "bullish"
    for i in range(len(df) - 1, max(st.broke_index - 30, 0), -1):
        c = df.iloc[i]
        is_bull = c["close"] > c["open"]
        if want_bull and not is_bull:
            out.append(OrderBlock("bullish", float(c["low"]), float(c["high"]), i, st.event))
            break
        if not want_bull and is_bull:
            out.append(OrderBlock("bearish", float(c["low"]), float(c["high"]), i, st.event))
            break
    return out


# ──────────────────────────────────────────────────────────────────────
# Position sizing — never below the 0.01 floor
# ──────────────────────────────────────────────────────────────────────

def calculate_lot_size(balance: float, risk_percent: float, entry: float,
                       stop_loss: float, tick_value: float, tick_size: float,
                       rules: Rules) -> float:
    """
    Risk-based sizing. tick_value / tick_size come from the broker's symbol
    info (mt5.symbol_info) — never hard-code them, they differ per symbol.
    """
    distance = abs(entry - stop_loss)
    if distance <= 0 or tick_size <= 0 or tick_value <= 0:
        return rules.base_lot

    risk_cash = balance * (risk_percent / 100.0)
    loss_per_lot = (distance / tick_size) * tick_value
    if loss_per_lot <= 0:
        return rules.base_lot

    raw = risk_cash / loss_per_lot
    stepped = round(raw / rules.lot_step) * rules.lot_step
    return float(min(max(stepped, rules.base_lot), rules.max_lot))


# ──────────────────────────────────────────────────────────────────────
# Time, sessions, news
# ──────────────────────────────────────────────────────────────────────

SESSIONS = {  # UTC open/close hours
    "Sydney": (21, 6), "Tokyo": (0, 9), "London": (7, 16), "New York": (12, 21),
}

SYMBOL_SESSIONS = {  # which sessions actually carry volatility for a symbol
    "EUR": ("London", "New York"), "GBP": ("London", "New York"),
    "JPY": ("Tokyo", "London"), "AUD": ("Sydney", "Tokyo"),
    "XAU": ("London", "New York"), "US30": ("New York",), "NAS": ("New York",),
    "OIL": ("New York",), "BTC": ("Sydney", "Tokyo", "London", "New York"),
}


def active_sessions(now_utc: datetime) -> List[str]:
    h = now_utc.hour
    out = []
    for name, (start, end) in SESSIONS.items():
        inside = start <= h < end if start < end else (h >= start or h < end)
        if inside:
            out.append(name)
    return out


def session_ok(symbol: str, now_utc: datetime) -> Tuple[bool, str]:
    live = active_sessions(now_utc)
    for key, wanted in SYMBOL_SESSIONS.items():
        if key in symbol.upper():
            hit = [s for s in live if s in wanted]
            return (bool(hit), ", ".join(hit) if hit else f"{'/'.join(wanted)} closed")
    return (True, ", ".join(live) or "off-session")


def news_block(symbol: str, events: List[Dict], now_utc: datetime,
               rules: Rules) -> Tuple[bool, str]:
    """
    events: [{"time": datetime (UTC), "impact": "high"|"medium"|"low",
              "currency": "USD", "title": "CPI m/m"}]
    Feed it from any calendar API — Forex Factory, FMP, Finnhub.
    """
    window = timedelta(minutes=rules.news_block_minutes)
    sym = symbol.upper()
    for ev in events:
        if ev.get("impact", "").lower() != "high":
            continue
        cur = ev.get("currency", "").upper()
        touches = cur in sym or (cur == "USD" and any(k in sym for k in ("XAU", "US30", "NAS", "OIL", "BTC")))
        if not touches:
            continue
        if abs(ev["time"] - now_utc) <= window:
            mins = int((ev["time"] - now_utc).total_seconds() // 60)
            return True, f"{ev.get('title','high-impact news')} in {mins} min"
    return False, "clear"


# ──────────────────────────────────────────────────────────────────────
# The decision
# ──────────────────────────────────────────────────────────────────────

def evaluate(symbol: str, df: pd.DataFrame, *, balance: float,
             tick_value: float, tick_size: float,
             open_positions: int = 0, daily_pnl: float = 0.0,
             news_events: Optional[List[Dict]] = None,
             now_utc: Optional[datetime] = None,
             rules: Optional[Rules] = None) -> Decision:
    """Run every rule in order. The first failure returns a rejection."""
    rules = rules or Rules()
    now_utc = now_utc or datetime.now(timezone.utc)
    news_events = news_events or []
    checks: List[Check] = []

    def reject(verdict: str, headline: str) -> Decision:
        return Decision(symbol=symbol, taken=False, verdict=verdict,
                        headline=headline, checks=checks)

    if len(df) < 60:
        return reject("Not enough history", f"Only {len(df)} bars available; need 60.")

    price = float(df["close"].iloc[-1])
    a = atr(df, 14)

    # 1 — capital guards
    if daily_pnl >= rules.daily_profit_cap:
        checks.append(Check("Daily profit cap", f"${daily_pnl:.2f} of ${rules.daily_profit_cap:.2f}", False))
        return reject("Daily cap hit", "Profit target reached — standing down to protect the balance.")
    if daily_pnl <= -abs(rules.max_daily_loss):
        checks.append(Check("Daily loss limit", f"${daily_pnl:.2f}", False))
        return reject("Daily loss limit", "Loss limit reached for today.")
    if open_positions >= rules.max_open_positions:
        checks.append(Check("Concurrent trade limit", f"{open_positions} of {rules.max_open_positions} used", False))
        return reject("Slots full", "Every position slot is already working.")
    checks.append(Check("Risk limits", f"{open_positions}/{rules.max_open_positions} open, ${daily_pnl:+.2f} today", True))

    # 2 — news
    blocked, note = news_block(symbol, news_events, now_utc, rules)
    checks.append(Check("High-impact news", note, not blocked))
    if blocked:
        return reject("News window", f"Entries muted — {note}.")

    # 3 — session volatility
    if rules.session_filter:
        ok, note = session_ok(symbol, now_utc)
        checks.append(Check("Session volatility", note, ok))
        if not ok:
            return reject("Session too thin", f"{symbol} is outside its liquid session ({note}).")

    # 4 — at a zone?
    zones = build_zones(df, rules)
    sup, res = nearest_zone(zones, price, "support"), nearest_zone(zones, price, "resistance")
    direction, zone = None, None
    if sup and sup.contains(price, rules.zone_touch_tolerance):
        direction, zone = "BUY", sup
    elif res and res.contains(price, rules.zone_touch_tolerance):
        direction, zone = "SELL", res
    if not direction:
        checks.append(Check("Price inside a zone", "mid-range", False))
        return reject("No zone", "Price is mid-range — the bot only enters at support or resistance.")
    checks.append(Check(f"Price inside {zone.kind}", f"{zone.low:.5f}–{zone.high:.5f}", True))

    # 5 — reversal confirmation
    pattern = reversal_candle(df, direction, rules)
    checks.append(Check("Reversal candle confirmed", pattern or "none", bool(pattern)))
    if rules.require_reversal_candle and not pattern:
        return reject("No confirmation", f"Price is at the {zone.kind} but no reversal candle has closed there.")

    # 6 — structure and its order block
    st = market_structure(df, rules)
    want = "bullish" if direction == "BUY" else "bearish"
    obs = [o for o in order_blocks(df, rules) if o.direction == want]
    checks.append(Check("Structure event", f"{st.event} {st.direction}", st.event != "none"))
    if rules.require_ob_structure and not obs:
        return reject("No order block", f"No {want} order block carrying a BOS or CHoCH at this level.")
    ob = obs[0] if obs else None
    if ob:
        checks.append(Check("Order block", f"{ob.low:.5f}–{ob.high:.5f} ({ob.event})", True))

    # 7 — fair value gap
    gaps = [g for g in find_fvgs(df, rules) if g.direction == want and not g.filled]
    checks.append(Check("Unfilled FVG in direction", f"{len(gaps)} found", bool(gaps)))
    if rules.require_fvg_unfilled and not gaps:
        return reject("No unfilled FVG", "Every gap in this direction has already been traded back through.")

    # 8 — levels and reward
    entry = price
    if direction == "BUY":
        stop = min(ob.low if ob else zone.low, zone.low) - a * 0.3
        target = res.mid if res else entry + (entry - stop) * 2
    else:
        stop = max(ob.high if ob else zone.high, zone.high) + a * 0.3
        target = sup.mid if sup else entry - (stop - entry) * 2

    risk = abs(entry - stop)
    reward = abs(target - entry)
    rr = reward / risk if risk > 0 else 0.0
    checks.append(Check("Reward to risk", f"{rr:.2f}R", rr >= rules.min_rr))
    if rr < rules.min_rr:
        return reject("Reward too small", f"Only {rr:.2f}R to the next zone; minimum is {rules.min_rr}R.")

    lots = calculate_lot_size(balance, rules.risk_percent, entry, stop,
                              tick_value, tick_size, rules)
    checks.append(Check("Lot size", f"{lots:.2f}", True))

    tags = [zone.kind.capitalize()]
    if ob:
        tags += [f"{ob.direction.capitalize()} OB", ob.event]
    if gaps:
        tags.append("FVG")

    return Decision(
        symbol=symbol, taken=True, direction=direction, entry=round(entry, 5),
        stop_loss=round(stop, 5), take_profit=round(target, 5), lots=lots,
        rr=round(rr, 2), tags=tags, checks=checks,
        headline=f"{pattern.capitalize()} closed inside the {zone.low:.5f}–{zone.high:.5f} "
                 f"{zone.kind}" + (f" with a {ob.direction} order block at {ob.event}." if ob else "."),
    )


# ──────────────────────────────────────────────────────────────────────
# Daily candle zones — the higher-timeframe map a manual trader draws first
# ──────────────────────────────────────────────────────────────────────

@dataclass
class DailyLevel:
    name: str
    price: float
    kind: str        # "resistance" | "support" | "pivot"

    def distance(self, price: float) -> float:
        return abs(self.price - price)


def daily_zones(daily: pd.DataFrame, price: float) -> List[DailyLevel]:
    """
    The levels worth marking from daily candles: yesterday's high, low and
    close, the current week's extremes, and the classic floor pivot set.
    Pass a D1 frame; returns them sorted by distance from price.
    """
    if daily is None or len(daily) < 3:
        return []

    y = daily.iloc[-2]                       # yesterday: the last CLOSED day
    yh, yl, yc = float(y["high"]), float(y["low"]), float(y["close"])
    today = daily.iloc[-1]

    pivot = (yh + yl + yc) / 3
    r1, s1 = 2 * pivot - yl, 2 * pivot - yh
    r2, s2 = pivot + (yh - yl), pivot - (yh - yl)

    week = daily.tail(5)
    wh, wl = float(week["high"].max()), float(week["low"].min())

    out = [
        DailyLevel("Yesterday high", yh, "resistance" if yh > price else "support"),
        DailyLevel("Yesterday low", yl, "support" if yl < price else "resistance"),
        DailyLevel("Yesterday close", yc, "pivot"),
        DailyLevel("Today open", float(today["open"]), "pivot"),
        DailyLevel("Week high", wh, "resistance" if wh > price else "support"),
        DailyLevel("Week low", wl, "support" if wl < price else "resistance"),
        DailyLevel("Pivot", pivot, "pivot"),
        DailyLevel("R1", r1, "resistance"), DailyLevel("S1", s1, "support"),
        DailyLevel("R2", r2, "resistance"), DailyLevel("S2", s2, "support"),
    ]
    return sorted(out, key=lambda l: l.distance(price))


def confluence(decision: "Decision", levels: List[DailyLevel], atr_value: float) -> List[str]:
    """Daily levels sitting on top of the entry — the reason a setup is A-grade."""
    if not decision.entry or not levels:
        return []
    near = atr_value * 0.6
    return [l.name for l in levels if l.distance(decision.entry) <= near]


def grade(decision: "Decision", confluences: List[str]) -> str:
    """A / B / C, the way you'd rank setups by eye before taking one."""
    if not decision.taken:
        return "—"
    score = 0
    score += 2 if (decision.rr or 0) >= 2.5 else 1 if (decision.rr or 0) >= 2 else 0
    score += min(len(confluences), 2)
    tags = " ".join(decision.tags).lower()
    score += 1 if "bos" in tags or "choch" in tags else 0
    score += 1 if "fvg" in tags else 0
    return "A" if score >= 5 else "B" if score >= 3 else "C"


# ──────────────────────────────────────────────────────────────────────
# Multi-timeframe reading
# ──────────────────────────────────────────────────────────────────────

@dataclass
class TFRead:
    """What one timeframe says, on its own."""
    timeframe: str
    bias: str              # "bullish" | "bearish" | "range"
    structure: str         # BOS / CHoCH / none
    at_zone: str           # "support" | "resistance" | "mid-range"
    reversal: Optional[str]
    price: float
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    unfilled_fvgs: int = 0
    order_block: Optional[str] = None

    @property
    def score(self) -> int:
        return {"bullish": 1, "bearish": -1}.get(self.bias, 0)


def read_timeframe(timeframe: str, df: pd.DataFrame,
                   rules: Optional[Rules] = None) -> TFRead:
    """A standalone verdict for one timeframe — no trade, just the reading."""
    rules = rules or Rules()
    price = float(df["close"].iloc[-1])
    st = market_structure(df, rules)

    zones = build_zones(df, rules)
    sup = nearest_zone(zones, price, "support")
    res = nearest_zone(zones, price, "resistance")

    at = "mid-range"
    if sup and sup.contains(price, rules.zone_touch_tolerance):
        at = "support"
    elif res and res.contains(price, rules.zone_touch_tolerance):
        at = "resistance"

    bias = st.direction if st.direction in ("bullish", "bearish") else "range"
    if st.event == "none" and bias == "range":
        # fall back to where price sits in its own recent range
        window = df.tail(60)
        span = float(window["high"].max()) - float(window["low"].min())
        if span > 0:
            pos = (price - float(window["low"].min())) / span
            bias = "bullish" if pos > 0.62 else "bearish" if pos < 0.38 else "range"

    want = "BUY" if at == "support" else "SELL" if at == "resistance" else None
    rev = reversal_candle(df, want, rules) if want else None

    obs = order_blocks(df, rules)
    gaps = [g for g in find_fvgs(df, rules) if not g.filled]

    return TFRead(
        timeframe=timeframe, bias=bias, structure=st.event, at_zone=at, reversal=rev,
        price=price,
        nearest_support=sup.mid if sup else None,
        nearest_resistance=res.mid if res else None,
        unfilled_fvgs=len(gaps),
        order_block=f"{obs[0].direction} {obs[0].event}" if obs else None,
    )


@dataclass
class MTFView:
    reads: Dict[str, TFRead]
    alignment: str          # "bullish" | "bearish" | "mixed"
    agreement: float        # 0–1, how much of the ladder agrees
    htf_bias: str           # what the slowest available timeframe says
    summary: str

    def agrees_with(self, direction: Optional[str]) -> bool:
        if not direction:
            return False
        want = "bullish" if direction == "BUY" else "bearish"
        return self.alignment == want


def multi_timeframe(frames: Dict[str, pd.DataFrame],
                    rules: Optional[Rules] = None,
                    weights: Optional[Dict[str, float]] = None) -> MTFView:
    """
    Read every timeframe given and combine them, slower frames weighing more.
    frames: {"M15": df, "H1": df, "H4": df, "D1": df}
    """
    rules = rules or Rules()
    weights = weights or {"M5": 0.5, "M15": 1.0, "M30": 1.2,
                          "H1": 1.6, "H4": 2.2, "D1": 3.0, "W1": 3.4}

    reads: Dict[str, TFRead] = {}
    for tf, df in frames.items():
        if df is None or len(df) < 60:
            continue
        try:
            reads[tf] = read_timeframe(tf, df, rules)
        except Exception:
            continue

    if not reads:
        return MTFView({}, "mixed", 0.0, "unknown", "No timeframe data available.")

    total = sum(weights.get(tf, 1.0) for tf in reads)
    signed = sum(weights.get(tf, 1.0) * r.score for tf, r in reads.items())
    ratio = signed / total if total else 0.0

    alignment = "bullish" if ratio >= 0.45 else "bearish" if ratio <= -0.45 else "mixed"
    agreement = round(abs(ratio), 2)

    order = ["W1", "D1", "H4", "H1", "M30", "M15", "M5"]
    htf = next((reads[t].bias for t in order if t in reads), "unknown")

    agreeing = [t for t, r in reads.items()
                if (r.bias == alignment)] if alignment != "mixed" else []
    if alignment == "mixed":
        summary = (f"Timeframes disagree — "
                   + ", ".join(f"{t} {r.bias}" for t, r in reads.items()) + ".")
    else:
        summary = (f"{', '.join(agreeing)} all read {alignment}"
                   f" ({int(agreement*100)}% weighted agreement), higher timeframe {htf}.")

    return MTFView(reads, alignment, agreement, htf, summary)


def mtf_grade(decision: "Decision", view: MTFView, confluences: List[str]) -> str:
    """Grade a setup with the timeframe stack folded in."""
    if not decision.taken:
        return "—"
    score = 0
    rr = decision.rr or 0
    score += 2 if rr >= 2.5 else 1 if rr >= 2 else 0
    score += min(len(confluences), 2)
    tags = " ".join(decision.tags).lower()
    score += 1 if ("bos" in tags or "choch" in tags) else 0
    score += 1 if "fvg" in tags else 0
    if view.agrees_with(decision.direction):
        score += 2 if view.agreement >= 0.7 else 1
    elif view.alignment != "mixed":
        score -= 2                      # trading against the stack
    return "A" if score >= 6 else "B" if score >= 4 else "C"
