"""
backtest.py — replay the rules over history.

Walks the candles bar by bar, asking strategy.evaluate() the same question the
live scanner asks, and follows each trade to its stop or target. No lookahead:
at bar i the engine only ever sees bars 0..i.

    from backtest import run
    result = run("XAUUSD", df, Rules())
    print(result.summary)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from strategy import Decision, Rules, evaluate


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_index: int
    entry_time: str
    entry: float
    stop: float
    target: float
    lots: float
    rr_planned: float
    exit_index: Optional[int] = None
    exit_time: str = ""
    exit_price: float = 0.0
    outcome: str = "open"        # win | loss | timeout | open
    r_multiple: float = 0.0
    bars_held: int = 0
    headline: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class Result:
    symbol: str
    trades: List[Trade]
    equity: List[float]
    rejections: Dict[str, int]
    bars: int

    @property
    def closed(self) -> List[Trade]:
        return [t for t in self.trades if t.outcome in ("win", "loss", "timeout")]

    @property
    def wins(self) -> List[Trade]:
        return [t for t in self.closed if t.outcome == "win"]

    @property
    def losses(self) -> List[Trade]:
        return [t for t in self.closed if t.outcome == "loss"]

    @property
    def win_rate(self) -> float:
        return len(self.wins) / len(self.closed) * 100 if self.closed else 0.0

    @property
    def total_r(self) -> float:
        return round(sum(t.r_multiple for t in self.closed), 2)

    @property
    def expectancy(self) -> float:
        return round(self.total_r / len(self.closed), 3) if self.closed else 0.0

    @property
    def profit_factor(self) -> float:
        won = sum(t.r_multiple for t in self.wins)
        lost = abs(sum(t.r_multiple for t in self.losses))
        return round(won / lost, 2) if lost else (99.0 if won else 0.0)

    @property
    def max_drawdown(self) -> float:
        peak, worst = 0.0, 0.0
        for v in self.equity:
            peak = max(peak, v)
            worst = min(worst, v - peak)
        return round(worst, 2)

    @property
    def longest_losing_streak(self) -> int:
        run = best = 0
        for t in self.closed:
            run = run + 1 if t.outcome == "loss" else 0
            best = max(best, run)
        return best

    @property
    def verdict(self) -> str:
        n = len(self.closed)
        if n < 10:
            return "Not enough trades to judge."
        if self.profit_factor >= 1.5 and self.expectancy > 0.2:
            return "Strong — the edge looks real on this sample."
        if self.profit_factor >= 1.2 and self.expectancy > 0:
            return "Workable — profitable, but the margin is thin."
        if self.profit_factor >= 1.0:
            return "Break-even. Tighten the rules before risking money."
        return "Losing on this sample. Do not trade these settings live."

    @property
    def summary(self) -> str:
        return (f"{len(self.closed)} trades · {self.win_rate:.0f}% win rate · "
                f"{self.total_r:+.1f}R · PF {self.profit_factor}")


def run(symbol: str, df: pd.DataFrame, rules: Rules, *,
        balance: float = 1000.0, tick_size: float = 0.0001,
        warmup: int = 120, max_bars_in_trade: int = 96,
        one_at_a_time: bool = True) -> Result:
    """
    Replay the rules over `df`. Entries are taken at the close of the
    confirming bar; exits check each later bar's high and low against the
    stop and target, stop first when a bar spans both (the pessimistic read).
    """
    trades: List[Trade] = []
    equity: List[float] = [0.0]
    rejections: Dict[str, int] = {}
    running = 0.0
    open_trade: Optional[Trade] = None

    n = len(df)
    if n < warmup + 30:
        return Result(symbol, [], equity, {}, n)

    for i in range(warmup, n):
        bar = df.iloc[i]

        # ── manage the open trade first ──
        if open_trade is not None:
            long = open_trade.direction == "BUY"
            hit_stop = (bar["low"] <= open_trade.stop) if long else (bar["high"] >= open_trade.stop)
            hit_target = (bar["high"] >= open_trade.target) if long else (bar["low"] <= open_trade.target)
            held = i - open_trade.entry_index

            done = None
            if hit_stop:                       # pessimistic: stop wins a tie
                done = ("loss", open_trade.stop, -1.0)
            elif hit_target:
                done = ("win", open_trade.target, open_trade.rr_planned)
            elif held >= max_bars_in_trade:
                risk = abs(open_trade.entry - open_trade.stop)
                move = ((bar["close"] - open_trade.entry) if long
                        else (open_trade.entry - bar["close"]))
                done = ("timeout", float(bar["close"]),
                        round(move / risk, 2) if risk else 0.0)

            if done:
                outcome, price, r = done
                open_trade.outcome = outcome
                open_trade.exit_price = price
                open_trade.exit_index = i
                open_trade.exit_time = str(bar["time"])
                open_trade.r_multiple = r
                open_trade.bars_held = held
                running += r
                equity.append(round(running, 3))
                open_trade = None

        if open_trade is not None and one_at_a_time:
            continue

        # ── look for a new entry using only bars up to i ──
        window = df.iloc[max(0, i - 400):i + 1].reset_index(drop=True)
        try:
            dec: Decision = evaluate(symbol, window, balance=balance,
                                     tick_value=1.0, tick_size=tick_size,
                                     open_positions=0, daily_pnl=0.0,
                                     rules=rules)
        except Exception:
            continue

        if not dec.taken:
            if dec.verdict:
                rejections[dec.verdict] = rejections.get(dec.verdict, 0) + 1
            continue

        open_trade = Trade(
            symbol=symbol, direction=dec.direction, entry_index=i,
            entry_time=str(bar["time"]), entry=float(dec.entry),
            stop=float(dec.stop_loss), target=float(dec.take_profit),
            lots=dec.lots, rr_planned=float(dec.rr or 0),
            headline=dec.headline, tags=list(dec.tags))
        trades.append(open_trade)

    return Result(symbol, trades, equity, rejections, n)


def sweep(symbol: str, df: pd.DataFrame, base: Rules,
          parameter: str, values: List, **kwargs) -> List[Dict]:
    """
    Run the same history repeatedly, changing one rule each time. Shows
    whether a setting actually earns its keep.
    """
    out = []
    for v in values:
        r = Rules(**{k: getattr(base, k) for k in base.__dataclass_fields__})
        setattr(r, parameter, v)
        res = run(symbol, df, r, **kwargs)
        out.append({"value": v, "trades": len(res.closed),
                    "win_rate": round(res.win_rate, 1), "total_r": res.total_r,
                    "expectancy": res.expectancy, "profit_factor": res.profit_factor,
                    "max_dd": res.max_drawdown})
    return out
