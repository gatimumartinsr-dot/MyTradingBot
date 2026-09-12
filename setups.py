"""
setups.py — the intelligence layer over the support & resistance playbook.

strategy.py holds the playbook and does not change: price must be at a level
price has respected before, and a reversal candle must close there. Nothing
here overrides that. This module adds what the specification asks for on top —
liquidity reading, named setup types, a transparent 0–100 confidence score,
staged targets and an invalidation condition.

    from setups import analyse_setup
    plan = analyse_setup(symbol, frames, decision, view, confluence, rules)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

from strategy import (Decision, Rules, atr, build_zones, find_fvgs,
                      market_structure, order_blocks, swing_points)

# ── the score card, straight from the spec ───────────────────────────

WEIGHTS = {
    "htf_trend": 20,
    "structure": 15,
    "liquidity": 15,
    "order_block": 10,
    "fvg": 10,
    "price_action": 10,
    "volatility": 5,
    "session": 5,
    "risk_reward": 10,
}

BANDS = [(90, "A+"), (80, "A"), (70, "B"), (60, "Weak")]
BAND_COLOR = {"A+": "#5fbf8f", "A": "#7fbf9a", "B": "#d2cefd",
              "Weak": "#d9b26a", "Ignore": "#5f6376"}

SETUP_TYPES = ["Liquidity Sweep", "Order Block", "Trend Pullback",
               "Breakout Retest", "S&R Reversal"]


# ──────────────────────────────────────────────────────────────────────
# Indicators the spec names
# ──────────────────────────────────────────────────────────────────────

def rsi(df: pd.DataFrame, period: int = 14) -> float:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    value = 100 - (100 / (1 + rs))
    out = float(value.iloc[-1])
    return out if out == out else 50.0


def range_state(df: pd.DataFrame, period: int = 14) -> Tuple[str, float]:
    """Is volatility expanding or contracting, and by how much."""
    a_now = atr(df.tail(period * 2), period)
    a_before = atr(df.tail(period * 4).head(period * 2), period)
    if not a_now or not a_before or a_before <= 0:
        return "normal", 1.0
    ratio = a_now / a_before
    if ratio >= 1.25:
        return "expanding", round(ratio, 2)
    if ratio <= 0.8:
        return "contracting", round(ratio, 2)
    return "normal", round(ratio, 2)


# ──────────────────────────────────────────────────────────────────────
# Liquidity
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Liquidity:
    equal_highs: List[float] = field(default_factory=list)
    equal_lows: List[float] = field(default_factory=list)
    sweep: Optional[str] = None          # "bullish" | "bearish"
    sweep_level: Optional[float] = None
    sweep_bars_ago: Optional[int] = None
    buyside: Optional[float] = None      # resting liquidity above
    sellside: Optional[float] = None     # resting liquidity below

    @property
    def note(self) -> str:
        if self.sweep == "bullish":
            return (f"Sell-side liquidity taken at {self.sweep_level:.5f} "
                    f"{self.sweep_bars_ago} bars ago, then price reclaimed it")
        if self.sweep == "bearish":
            return (f"Buy-side liquidity taken at {self.sweep_level:.5f} "
                    f"{self.sweep_bars_ago} bars ago, then price rejected")
        pools = []
        if self.buyside:
            pools.append(f"{self.buyside:.5f} above")
        if self.sellside:
            pools.append(f"{self.sellside:.5f} below")
        return "Resting liquidity at " + " and ".join(pools) if pools else "No clear pools"


def find_liquidity(df: pd.DataFrame, rules: Optional[Rules] = None,
                   tolerance_atr: float = 0.18, lookback: int = 60) -> Liquidity:
    """
    Equal highs and lows are where stops pile up. A sweep is price poking
    through one of them and closing back the other side — a stop run.
    """
    rules = rules or Rules()
    out = Liquidity()
    if len(df) < 40:
        return out

    a = atr(df, 14)
    if not a or a != a:
        return out
    tol = a * tolerance_atr

    highs, lows = swing_points(df, rules.swing_lookback)
    recent_h = [i for i in highs if i >= len(df) - lookback]
    recent_l = [i for i in lows if i >= len(df) - lookback]

    def clusters(indices, col):
        vals = sorted(float(df[col].values[i]) for i in indices)
        groups, cur = [], []
        for v in vals:
            if cur and v - cur[-1] > tol:
                if len(cur) >= 2:
                    groups.append(sum(cur) / len(cur))
                cur = []
            cur.append(v)
        if len(cur) >= 2:
            groups.append(sum(cur) / len(cur))
        return groups

    out.equal_highs = clusters(recent_h, "high")
    out.equal_lows = clusters(recent_l, "low")

    price = float(df["close"].iloc[-1])
    above = [v for v in out.equal_highs if v > price] or \
            [float(df["high"].values[i]) for i in recent_h if float(df["high"].values[i]) > price]
    below = [v for v in out.equal_lows if v < price] or \
            [float(df["low"].values[i]) for i in recent_l if float(df["low"].values[i]) < price]
    out.buyside = min(above) if above else None
    out.sellside = max(below) if below else None

    # a sweep: within the last 12 bars, price traded through a pool and closed back
    window = min(12, len(df) - 1)
    for back in range(1, window + 1):
        bar = df.iloc[-back]
        for pool in out.equal_lows:
            if bar["low"] < pool - tol * 0.4 and bar["close"] > pool:
                out.sweep, out.sweep_level, out.sweep_bars_ago = "bullish", pool, back
                return out
        for pool in out.equal_highs:
            if bar["high"] > pool + tol * 0.4 and bar["close"] < pool:
                out.sweep, out.sweep_level, out.sweep_bars_ago = "bearish", pool, back
                return out
    return out


# ──────────────────────────────────────────────────────────────────────
# Session levels
# ──────────────────────────────────────────────────────────────────────

SESSION_HOURS = {"Asian": (0, 9), "London": (7, 16), "New York": (12, 21)}


@dataclass
class SessionLevel:
    session: str
    high: float
    low: float


def session_levels(df: pd.DataFrame, now: Optional[datetime] = None) -> List[SessionLevel]:
    """Today's high and low for each session — the levels intraday traders watch."""
    now = now or datetime.now(timezone.utc)
    if "time" not in df.columns or len(df) < 20:
        return []
    today = df[df["time"] >= pd.Timestamp(now.date(), tz="UTC")]
    if len(today) < 4:
        today = df.tail(96)
    out = []
    for name, (a, b) in SESSION_HOURS.items():
        hours = today["time"].dt.hour
        seg = today[(hours >= a) & (hours < b)] if a < b else \
              today[(hours >= a) | (hours < b)]
        if len(seg) >= 3:
            out.append(SessionLevel(name, float(seg["high"].max()),
                                    float(seg["low"].min())))
    return out


def active_session(now: Optional[datetime] = None) -> List[str]:
    now = now or datetime.now(timezone.utc)
    return [n for n, (a, b) in SESSION_HOURS.items()
            if (a <= now.hour < b if a < b else now.hour >= a or now.hour < b)]


# ──────────────────────────────────────────────────────────────────────
# Extra price action the spec names
# ──────────────────────────────────────────────────────────────────────

def price_action(df: pd.DataFrame, direction: str) -> List[str]:
    """Every pattern present on the last closed candle, not just the first."""
    if len(df) < 4:
        return []
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    rng = c3["high"] - c3["low"]
    if rng <= 0:
        return []
    body = abs(c3["close"] - c3["open"])
    bull = c3["close"] > c3["open"]
    lower = min(c3["open"], c3["close"]) - c3["low"]
    upper = c3["high"] - max(c3["open"], c3["close"])
    found = []

    if direction == "BUY":
        if lower > rng * 0.55 and body < rng * 0.4:
            found.append("hammer" if bull else "pin bar")
        if bull and c3["close"] >= c2["open"] and c2["close"] < c2["open"]:
            found.append("bullish engulfing")
        if bull and lower > rng * 0.3 and c3["close"] > c2["high"]:
            found.append("rejection close")
    else:
        if upper > rng * 0.55 and body < rng * 0.4:
            found.append("shooting star" if not bull else "pin bar")
        if not bull and c3["close"] <= c2["open"] and c2["close"] > c2["open"]:
            found.append("bearish engulfing")
        if not bull and upper > rng * 0.3 and c3["close"] < c2["low"]:
            found.append("rejection close")

    if c3["high"] <= c2["high"] and c3["low"] >= c2["low"]:
        found.append("inside bar")

    a = atr(df, 14)
    if a and body > a * 1.6:
        found.append("displacement")
    return found


# ──────────────────────────────────────────────────────────────────────
# Setup type
# ──────────────────────────────────────────────────────────────────────

def classify(decision: Decision, liq: Liquidity, df: pd.DataFrame,
             rules: Rules) -> Tuple[str, str]:
    """Name the setup and say in one line why it is that name."""
    if not decision.taken:
        return "—", ""
    want = "bullish" if decision.direction == "BUY" else "bearish"
    st = market_structure(df, rules)
    obs = [o for o in order_blocks(df, rules) if o.direction == want]
    state, ratio = range_state(df)

    if liq.sweep == want:
        return ("Liquidity Sweep",
                f"stops were run at {liq.sweep_level:.5f} and price reclaimed the level")
    if obs and st.event in ("BOS", "CHoCH"):
        if st.event == "CHoCH":
            return ("Order Block",
                    f"a change of character built this block, so the prior trend has turned")
        return ("Trend Pullback" if st.direction == want else "Order Block",
                f"price pulled back into the block that created the last {st.event}")
    if state == "expanding" and st.event == "BOS":
        return ("Breakout Retest",
                f"volatility expanded {ratio:g}× through the level, and price came back to it")
    return ("S&R Reversal", "price turned at a level it has respected before")


# ──────────────────────────────────────────────────────────────────────
# Confidence score
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Factor:
    name: str
    weight: int
    earned: int
    detail: str

    @property
    def pct(self) -> float:
        return self.earned / self.weight * 100 if self.weight else 0.0


@dataclass
class Score:
    total: int
    band: str
    factors: List[Factor]
    news_penalty: int = 0
    news_note: str = ""

    @property
    def tradeable(self) -> bool:
        return self.band in ("A+", "A", "B")

    @property
    def color(self) -> str:
        return BAND_COLOR[self.band]

    @property
    def earned_factors(self) -> List[Factor]:
        return [f for f in self.factors if f.earned > 0]

    @property
    def missing_factors(self) -> List[Factor]:
        return [f for f in self.factors if f.earned == 0]


def band_for(total: int) -> str:
    for floor, name in BANDS:
        if total >= floor:
            return name
    return "Ignore"


def score_setup(decision: Decision, view, confluences: List[str], liq: Liquidity,
                df: pd.DataFrame, rules: Rules, *, news_minutes: Optional[int] = None,
                news_title: str = "") -> Score:
    """
    Every point is attributable. The factors and weights are the spec's;
    the underlying checks are the playbook's.
    """
    factors: List[Factor] = []

    def add(key, earned, detail):
        factors.append(Factor(key.replace("_", " ").title(), WEIGHTS[key],
                              int(round(earned)), detail))

    if not decision.taken:
        for k in WEIGHTS:
            add(k, 0, "no setup")
        return Score(0, "Ignore", factors)

    want = "bullish" if decision.direction == "BUY" else "bearish"
    tags = " ".join(decision.tags).lower()

    # 1 — higher-timeframe trend, the heaviest factor
    if view and view.agrees_with(decision.direction):
        earned = WEIGHTS["htf_trend"] * (1.0 if view.agreement >= 0.7 else 0.7)
        add("htf_trend", earned,
            f"{view.alignment} at {int(view.agreement*100)}% agreement")
    elif view and view.alignment == "mixed":
        add("htf_trend", WEIGHTS["htf_trend"] * 0.35, "timeframes are mixed")
    else:
        add("htf_trend", 0, f"stack reads {getattr(view, 'alignment', 'unknown')} — against this trade")

    # 2 — market structure
    st = market_structure(df, rules)
    if st.event == "BOS" and st.direction == want:
        add("structure", WEIGHTS["structure"], "break of structure in this direction")
    elif st.event == "CHoCH" and st.direction == want:
        add("structure", WEIGHTS["structure"] * 0.8, "change of character in this direction")
    elif st.event != "none":
        add("structure", WEIGHTS["structure"] * 0.3, f"{st.event} {st.direction}")
    else:
        add("structure", 0, "no structure break yet")

    # 3 — liquidity
    if liq.sweep == want:
        add("liquidity", WEIGHTS["liquidity"],
            f"stop run at {liq.sweep_level:.5f}, {liq.sweep_bars_ago} bars ago")
    elif liq.equal_highs or liq.equal_lows:
        add("liquidity", WEIGHTS["liquidity"] * 0.4,
            f"{len(liq.equal_highs)} equal highs, {len(liq.equal_lows)} equal lows")
    else:
        add("liquidity", 0, "no liquidity pools nearby")

    # 4 — order block
    ob_check = next((c for c in decision.checks if c.label == "Order block"), None)
    if ob_check:
        add("order_block", WEIGHTS["order_block"], ob_check.value)
    else:
        add("order_block", 0, "no qualifying order block")

    # 5 — fair value gap
    gaps = [g for g in find_fvgs(df, rules) if not g.filled and g.direction == want]
    if gaps:
        a = atr(df, 14) or 1
        big = max(gaps, key=lambda g: g.size)
        earned = WEIGHTS["fvg"] * (1.0 if big.size >= a * 0.5 else 0.6)
        add("fvg", earned, f"{len(gaps)} unfilled, largest {big.size / a:.1f}× ATR")
    else:
        add("fvg", 0, "every gap already filled")

    # 6 — price action
    patterns = price_action(df, decision.direction)
    if patterns:
        weight = WEIGHTS["price_action"]
        strong = any(p in patterns for p in ("bullish engulfing", "bearish engulfing",
                                             "displacement", "hammer", "shooting star"))
        add("price_action", weight * (1.0 if strong else 0.6), ", ".join(patterns))
    else:
        add("price_action", 0, "no confirming candle shape")

    # 7 — volatility
    state, ratio = range_state(df)
    if state == "expanding":
        add("volatility", WEIGHTS["volatility"], f"range expanding {ratio:g}×")
    elif state == "normal":
        add("volatility", WEIGHTS["volatility"] * 0.6, f"volatility normal, {ratio:g}×")
    else:
        add("volatility", 0, f"range contracting {ratio:g}× — moves may stall")

    # 8 — session
    live = active_session()
    sym_upper = decision.symbol.upper()
    good = (("London" in live or "New York" in live) if
            any(k in sym_upper for k in ("EUR", "GBP", "XAU", "US30", "NAS", "SPX", "OIL"))
            else bool(live))
    if good:
        add("session", WEIGHTS["session"], " + ".join(live) + " open")
    elif live:
        add("session", WEIGHTS["session"] * 0.5, " + ".join(live) + " — thin for this symbol")
    else:
        add("session", 0, "outside the main sessions")

    # 9 — reward to risk
    rr = decision.rr or 0
    if rr >= 3:
        add("risk_reward", WEIGHTS["risk_reward"], f"{rr}R to the next level")
    elif rr >= 2:
        add("risk_reward", WEIGHTS["risk_reward"] * 0.8, f"{rr}R")
    elif rr >= rules.min_rr:
        add("risk_reward", WEIGHTS["risk_reward"] * 0.5, f"{rr}R, only just clears the minimum")
    else:
        add("risk_reward", 0, f"{rr}R is below your {rules.min_rr}R minimum")

    if confluences:
        for f in factors:
            if f.name == "Htf Trend":
                f.earned = min(f.weight, f.earned + 2)
                f.detail += f" · daily levels on the entry: {', '.join(confluences)}"

    total = sum(f.earned for f in factors)

    penalty, note = 0, ""
    if news_minutes is not None and news_minutes <= rules.news_block_minutes:
        penalty = 25 if news_minutes <= 15 else 15
        note = f"{news_title or 'High-impact news'} in {news_minutes} min"
    elif news_minutes is not None and news_minutes <= rules.news_block_minutes * 2:
        penalty = 5
        note = f"{news_title or 'News'} in {news_minutes} min"

    total = max(0, min(100, total - penalty))
    return Score(int(round(total)), band_for(total), factors, penalty, note)


# ──────────────────────────────────────────────────────────────────────
# Trade plan
# ──────────────────────────────────────────────────────────────────────

@dataclass
class TradePlan:
    symbol: str
    mt5: str
    direction: str
    setup_type: str
    setup_reason: str
    timeframe: str
    entry: float
    entry_low: float
    entry_high: float
    stop: float
    tp1: float
    tp2: float
    tp3: float
    rr1: float
    rr2: float
    rr3: float
    lots: float
    score: Score
    liquidity: Liquidity
    alignment: str
    reasons: List[str]
    invalidation: str
    news_warning: str
    digits: int = 5

    @property
    def rank_key(self):
        return (-self.score.total, -self.rr2)

    def summary(self) -> str:
        return (f"{self.mt5} {self.direction} · {self.setup_type} · "
                f"{self.score.total}% · 1:{self.rr2:g}")

    def telegram(self) -> str:
        d = self.digits
        body = (f"<b>{self.score.band} · {self.mt5} {self.direction}</b>\n"
                f"{self.setup_type} · {self.timeframe} · confidence {self.score.total}%\n\n"
                f"Entry <code>{self.entry_low:,.{d}f}–{self.entry_high:,.{d}f}</code>\n"
                f"SL   <code>{self.stop:,.{d}f}</code>\n"
                f"TP1  <code>{self.tp1:,.{d}f}</code>  (1:{self.rr1:g})\n"
                f"TP2  <code>{self.tp2:,.{d}f}</code>  (1:{self.rr2:g})\n"
                f"TP3  <code>{self.tp3:,.{d}f}</code>  (1:{self.rr3:g})\n"
                f"{self.lots:.2f} lots\n\n<b>Why</b>\n")
        body += "\n".join(f"• {r}" for r in self.reasons[:5])
        body += f"\n\n<b>Invalid if</b> {self.invalidation}"
        if self.news_warning:
            body += f"\n⚠ {self.news_warning}"
        return body


def build_plan(symbol: str, mt5_name: str, digits: int, decision: Decision,
               df: pd.DataFrame, view, confluences: List[str], rules: Rules, *,
               timeframe: str = "M15", news_minutes: Optional[int] = None,
               news_title: str = "", reasons: Optional[List[str]] = None
               ) -> Optional[TradePlan]:
    """Everything the spec's trade-plan output asks for, in one object."""
    if not decision.taken:
        return None

    liq = find_liquidity(df, rules)
    score = score_setup(decision, view, confluences, liq, df, rules,
                        news_minutes=news_minutes, news_title=news_title)
    setup_type, setup_reason = classify(decision, liq, df, rules)

    entry, stop = float(decision.entry), float(decision.stop_loss)
    risk = abs(entry - stop)
    long = decision.direction == "BUY"
    a = atr(df, 14) or risk

    # entry zone rather than a single price — the spec asks for a zone
    pad = min(risk * 0.25, a * 0.3)
    entry_low = entry - pad if long else entry
    entry_high = entry if long else entry + pad

    # staged targets: the structural target is TP2, with a nearer and further one
    structural = float(decision.take_profit)
    r_struct = abs(structural - entry) / risk if risk else 1.0
    r1 = max(1.0, round(r_struct * 0.55, 2))
    r2 = round(max(r_struct, rules.min_rr), 2)
    r3 = round(r2 * 1.6, 2)

    def target(mult):
        return entry + risk * mult if long else entry - risk * mult

    tp1, tp2, tp3 = target(r1), target(r2), target(r3)

    why = list(reasons or [])
    why.insert(0, f"{setup_type} — {setup_reason}.")
    if liq.sweep:
        why.append(liq.note + ".")
    if score.news_note:
        why.append(f"Score reduced {score.news_penalty} points: {score.news_note}.")

    zone_word = "support" if long else "resistance"
    invalid = (f"a candle closes {'below' if long else 'above'} "
               f"{stop:,.{digits}f} — that breaks the {zone_word} the whole idea rests on")

    return TradePlan(
        symbol=symbol, mt5=mt5_name, direction=decision.direction,
        setup_type=setup_type, setup_reason=setup_reason, timeframe=timeframe,
        entry=entry, entry_low=entry_low, entry_high=entry_high, stop=stop,
        tp1=tp1, tp2=tp2, tp3=tp3, rr1=r1, rr2=r2, rr3=r3,
        lots=float(decision.lots), score=score, liquidity=liq,
        alignment=getattr(view, "alignment", "unknown"), reasons=why,
        invalidation=invalid, news_warning=score.news_note, digits=digits)


# ──────────────────────────────────────────────────────────────────────
# Currency strength — the spec's sentiment panel
# ──────────────────────────────────────────────────────────────────────

PAIR_LEGS = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "USDJPY": ("USD", "JPY"),
    "AUDUSD": ("AUD", "USD"), "USDCAD": ("USD", "CAD"), "USDCHF": ("USD", "CHF"),
    "NZDUSD": ("NZD", "USD"), "XAUUSD": ("XAU", "USD"),
}


def currency_strength(changes: Dict[str, float]) -> List[Tuple[str, float]]:
    """
    Turn per-pair daily moves into a per-currency score, 0–100.
    changes: {"EURUSD": +0.32, ...} in percent.
    """
    tally: Dict[str, List[float]] = {}
    for pair, pct in changes.items():
        legs = PAIR_LEGS.get(pair.upper())
        if not legs:
            continue
        base, quote = legs
        tally.setdefault(base, []).append(pct)
        tally.setdefault(quote, []).append(-pct)
    if not tally:
        return []
    avg = {k: sum(v) / len(v) for k, v in tally.items()}
    lo, hi = min(avg.values()), max(avg.values())
    span = hi - lo or 1.0
    return sorted(((k, round((v - lo) / span * 100)) for k, v in avg.items()),
                  key=lambda x: -x[1])
