"""
visuals.py — inline SVG explainers for people who have never traded.

Every concept the engine uses, drawn. No libraries: each function returns a
self-contained SVG string sized to fit a panel, themed to Nocturne tokens.
"""

BG, SURFACE, RAISED = "#161826", "#1e2030", "#252838"
TEXT, MUTED, FAINT = "#e9e9ed", "#9397ab", "#5f6376"
ACCENT, A300 = "#9184d9", "#d2cefd"
UP, DOWN, WARN = "#5fbf8f", "#e07b87", "#d9b26a"
GRID = "rgba(233,233,237,.07)"

FONT = "Inter, system-ui, sans-serif"
MONO = "JetBrains Mono, monospace"


def _candle(x, o, c, h, l, w=9):
    """One candle. Prices are already in SVG y-space (smaller y = higher price)."""
    col = UP if c < o else DOWN          # y inverted: lower y means higher price
    top, bot = min(o, c), max(o, c)
    body = max(bot - top, 1.5)
    return (f'<rect x="{x + w/2 - 0.7:.1f}" y="{h:.1f}" width="1.4" '
            f'height="{max(l - h, 1):.1f}" fill="{col}"/>'
            f'<rect x="{x:.1f}" y="{top:.1f}" width="{w}" height="{body:.1f}" '
            f'rx="1" fill="{col}"/>')


def _label(x, y, text, color=MUTED, size=9.5, anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-family="{FONT}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{text}</text>')


def _zone(y, h, color, label, w=330, x=0):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}22" '
            f'stroke="{color}" stroke-width="1" rx="2"/>'
            + _label(x + 5, y + h / 2 + 3, label, color, 9, "start", "500"))


def _frame(inner, w=340, h=190):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" '
            f'style="display:block;background:{BG};border-radius:8px">{inner}</svg>')


# ──────────────────────────────────────────────────────────────────────

def support_resistance() -> str:
    """Price bouncing off a floor and a ceiling."""
    inner = [_zone(28, 20, DOWN, "RESISTANCE — the ceiling"),
             _zone(140, 20, UP, "SUPPORT — the floor")]
    # price wandering between them, touching each twice
    path = [(0, 120, 118, 108, 132), (16, 108, 128, 100, 140), (32, 128, 145, 122, 152),
            (48, 145, 132, 126, 150), (64, 132, 112, 105, 138), (80, 112, 92, 84, 118),
            (96, 92, 70, 60, 98), (112, 70, 52, 42, 76), (128, 52, 40, 34, 58),
            (144, 40, 50, 34, 58), (160, 50, 66, 44, 72), (176, 66, 88, 60, 96),
            (192, 88, 110, 82, 118), (208, 110, 132, 104, 142), (224, 132, 146, 126, 154),
            (240, 146, 134, 128, 152), (256, 134, 116, 108, 142), (272, 116, 96, 88, 122),
            (288, 96, 78, 70, 104), (304, 78, 62, 54, 86), (320, 62, 48, 40, 70)]
    for x, o, c, h, l in path:
        inner.append(_candle(x, o, c, h, l))
    inner += [
        f'<circle cx="140" cy="150" r="11" fill="none" stroke="{UP}" stroke-width="1.3"/>',
        f'<circle cx="230" cy="150" r="11" fill="none" stroke="{UP}" stroke-width="1.3"/>',
        f'<circle cx="136" cy="38" r="11" fill="none" stroke="{DOWN}" stroke-width="1.3"/>',
        _label(170, 178, "Price turns at the same levels again and again",
               MUTED, 9.5, "middle"),
    ]
    return _frame("".join(inner))


def fair_value_gap() -> str:
    """Three candles with a gap between candle 1 and candle 3."""
    inner = [
        _label(0, 14, "A fast move leaves a gap price has not traded through",
               MUTED, 9.5),
        # slow candles
        _candle(20, 120, 112, 106, 126, 14), _candle(44, 112, 118, 106, 126, 14),
        _candle(68, 118, 108, 100, 124, 14),
        # the impulse: candle 1, big candle 2, candle 3 — no overlap 1 to 3
        _candle(100, 108, 96, 92, 112, 14),
        _candle(124, 92, 56, 52, 96, 14),
        _candle(148, 52, 44, 40, 56, 14),
        # the gap itself
        f'<rect x="96" y="56" width="230" height="36" fill="{ACCENT}26" '
        f'stroke="{ACCENT}" stroke-width="1" stroke-dasharray="4 3" rx="2"/>',
        _label(180, 78, "FAIR VALUE GAP", A300, 10, "start", "600"),
        # later candles drifting back toward it
        _candle(180, 44, 52, 40, 58, 14), _candle(204, 52, 46, 42, 58, 14),
        _candle(228, 46, 58, 42, 64, 14), _candle(252, 58, 66, 54, 72, 14),
        _candle(276, 66, 60, 56, 74, 14),
        f'<path d="M300 64 L316 76" stroke="{A300}" stroke-width="1.3" '
        f'marker-end="url(#ar)"/>',
        f'<defs><marker id="ar" markerWidth="6" markerHeight="6" refX="5" refY="3" '
        f'orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="{A300}"/></marker></defs>',
        _label(170, 172, "Price tends to come back and fill it", A300, 9.5, "middle"),
    ]
    return _frame("".join(inner))


def order_block() -> str:
    """The last opposite candle before the move that broke structure."""
    inner = [
        _label(0, 14, "The candle big money left behind before the breakout", MUTED, 9.5),
        f'<line x1="0" x2="340" y1="60" y2="60" stroke="{WARN}" stroke-width="1" '
        f'stroke-dasharray="4 3"/>',
        _label(336, 55, "old high", WARN, 9, "end"),
        _candle(16, 124, 116, 110, 130, 12), _candle(38, 116, 126, 110, 132, 12),
        _candle(60, 126, 118, 112, 132, 12), _candle(82, 118, 128, 112, 134, 12),
        # the order block — last red candle before the impulse
        f'<rect x="100" y="112" width="226" height="26" fill="{WARN}26" '
        f'stroke="{WARN}" stroke-width="1" rx="2"/>',
        _candle(104, 116, 134, 112, 138, 12),
        _label(200, 128, "ORDER BLOCK", WARN, 10, "start", "600"),
        # impulse breaking the old high
        _candle(126, 134, 96, 92, 136, 12),
        _candle(148, 96, 54, 50, 98, 12),
        _candle(170, 54, 42, 38, 58, 12),
        _label(196, 46, "break of structure", UP, 9.5),
        # pullback into the block
        _candle(192, 42, 62, 40, 68, 12), _candle(214, 62, 84, 58, 90, 12),
        _candle(236, 84, 106, 80, 112, 12), _candle(258, 106, 122, 100, 128, 12),
        _candle(280, 122, 104, 100, 130, 12), _candle(302, 104, 82, 76, 110, 12),
        f'<circle cx="286" cy="126" r="11" fill="none" stroke="{UP}" stroke-width="1.3"/>',
        _label(170, 172, "Price returns to it, then continues — that is the entry",
               MUTED, 9.5, "middle"),
    ]
    return _frame("".join(inner))


def bos_choch() -> str:
    """Break of structure versus change of character, side by side."""
    inner = [
        _label(0, 14, "BOS — trend continues", UP, 10, "start", "600"),
        _label(178, 14, "CHoCH — trend flips", DOWN, 10, "start", "600"),
        f'<line x1="168" x2="168" y1="24" y2="176" stroke="{GRID}" stroke-width="1"/>',
        # BOS: higher highs, breaks the last high
        f'<path d="M8 140 L38 96 L26 118 L62 62 L50 84 L92 34" fill="none" '
        f'stroke="{UP}" stroke-width="1.8" stroke-linejoin="round"/>',
        f'<line x1="30" x2="150" y1="62" y2="62" stroke="{WARN}" stroke-width="1" '
        f'stroke-dasharray="3 3"/>',
        _label(146, 58, "high", WARN, 8.5, "end"),
        f'<path d="M92 34 L128 52 L150 22" fill="none" stroke="{UP}" '
        f'stroke-width="1.8" stroke-linejoin="round"/>',
        f'<circle cx="150" cy="22" r="7" fill="none" stroke="{UP}" stroke-width="1.3"/>',
        _label(84, 166, "keeps making higher highs", MUTED, 9, "middle"),
        # CHoCH: uptrend then breaks the last low
        f'<path d="M186 130 L214 88 L204 108 L238 56 L228 76 L258 44" fill="none" '
        f'stroke="{UP}" stroke-width="1.8" stroke-linejoin="round"/>',
        f'<line x1="200" x2="330" y1="108" y2="108" stroke="{WARN}" stroke-width="1" '
        f'stroke-dasharray="3 3"/>',
        _label(326, 104, "low", WARN, 8.5, "end"),
        f'<path d="M258 44 L284 86 L276 70 L312 136" fill="none" stroke="{DOWN}" '
        f'stroke-width="1.8" stroke-linejoin="round"/>',
        f'<circle cx="312" cy="136" r="7" fill="none" stroke="{DOWN}" stroke-width="1.3"/>',
        _label(258, 166, "breaks a low instead", MUTED, 9, "middle"),
    ]
    return _frame("".join(inner))


def reversal_candles() -> str:
    """The three shapes the engine accepts as confirmation."""
    def pair(x, kind):
        out = []
        if kind == "engulf":
            out += [_candle(x + 4, 60, 96, 54, 102, 16),
                    _candle(x + 28, 98, 52, 48, 104, 16)]
            t = "Engulfing"
            d = "A green candle swallows the red one before it"
        elif kind == "pin":
            out += [_candle(x + 4, 62, 72, 56, 78, 16),
                    f'<rect x="{x+34.3}" y="62" width="1.4" height="46" fill="{UP}"/>'
                    f'<rect x="{x+28}" y="56" width="16" height="8" rx="1" fill="{UP}"/>']
            t = "Pin bar"
            d = "A long tail — sellers tried and failed"
        else:
            out += [_candle(x + 2, 54, 84, 50, 90, 13),
                    _candle(x + 20, 86, 90, 82, 96, 13),
                    _candle(x + 38, 90, 58, 54, 94, 13)]
            t = "Morning star"
            d = "Down, pause, then up"
        out.append(_label(x + 30, 128, t, TEXT, 10, "middle", "500"))
        return "".join(out), d

    blocks, notes = [], []
    for i, kind in enumerate(["engulf", "pin", "star"]):
        svg, note = pair(i * 113, kind)
        blocks.append(svg)
        notes.append(note)

    inner = [_label(0, 14, "The engine only enters after one of these CLOSES", MUTED, 9.5)]
    inner += blocks
    for i, n in enumerate(notes):
        inner.append(_label(i * 113 + 30, 148, n[:22], FAINT, 8, "middle"))
        if len(n) > 22:
            inner.append(_label(i * 113 + 30, 159, n[22:], FAINT, 8, "middle"))
    for i in (1, 2):
        inner.append(f'<line x1="{i*113-4}" x2="{i*113-4}" y1="30" y2="140" '
                     f'stroke="{GRID}" stroke-width="1"/>')
    return _frame("".join(inner), 340, 172)


def risk_reward(rr: float = 2.0) -> str:
    """Entry, stop and target drawn to scale."""
    entry_y = 104
    risk_px = 34
    reward_px = min(risk_px * rr, 74)
    stop_y = entry_y + risk_px
    tp_y = entry_y - reward_px

    inner = [
        f'<rect x="60" y="{tp_y}" width="212" height="{entry_y - tp_y}" '
        f'fill="{UP}1e" rx="2"/>',
        f'<rect x="60" y="{entry_y}" width="212" height="{risk_px}" fill="{DOWN}1e" rx="2"/>',
        f'<line x1="40" x2="300" y1="{entry_y}" y2="{entry_y}" stroke="#6ba4f0" '
        f'stroke-width="1.6"/>',
        f'<line x1="40" x2="300" y1="{stop_y}" y2="{stop_y}" stroke="{DOWN}" '
        f'stroke-width="1.6" stroke-dasharray="5 3"/>',
        f'<line x1="40" x2="300" y1="{tp_y}" y2="{tp_y}" stroke="{UP}" '
        f'stroke-width="1.6" stroke-dasharray="5 3"/>',
        _label(304, entry_y + 3.5, "ENTRY", "#6ba4f0", 9.5, "start", "600"),
        _label(304, stop_y + 3.5, "STOP", DOWN, 9.5, "start", "600"),
        _label(304, tp_y + 3.5, "TARGET", UP, 9.5, "start", "600"),
        _label(56, entry_y + risk_px / 2 + 3, "risk", DOWN, 9, "end"),
        _label(56, entry_y - reward_px / 2 + 3, f"reward {rr:g}×", UP, 9, "end"),
        _label(166, 176, f"Lose 1 unit if wrong, make {rr:g} if right",
               MUTED, 9.5, "middle"),
    ]
    for i, (x, o, c, h, l) in enumerate([
            (72, 128, 118, 112, 134), (96, 118, 130, 112, 136), (120, 130, 120, 114, 138),
            (144, 120, 136, 114, 140), (168, 138, 106, 102, 140),
            (192, 106, 92, 84, 110), (216, 92, 74, 66, 98), (240, 74, 56, 48, 80)]):
        inner.append(_candle(x, o, c, h, l, 11))
    return _frame("".join(inner), 340, 190)


def daily_zones() -> str:
    """Yesterday's candle projected forward as today's map."""
    inner = [
        _label(0, 13, "Yesterday's daily candle becomes today's map", MUTED, 9.5),
        # yesterday's big daily candle on the left
        f'<rect x="24" y="34" width="1.6" height="120" fill="{UP}"/>',
        f'<rect x="14" y="52" width="22" height="86" rx="2" fill="{UP}"/>',
        _label(25, 168, "yesterday", FAINT, 8.5, "middle"),
        # its levels projected right
        f'<line x1="44" x2="330" y1="34" y2="34" stroke="{DOWN}" stroke-width="1.2" '
        f'stroke-dasharray="5 3"/>',
        _label(326, 30, "yesterday high", DOWN, 8.5, "end"),
        f'<line x1="44" x2="330" y1="52" y2="52" stroke="{FAINT}" stroke-width="1" '
        f'stroke-dasharray="3 3"/>',
        _label(326, 48, "close", FAINT, 8.5, "end"),
        f'<line x1="44" x2="330" y1="94" y2="94" stroke="{ACCENT}" stroke-width="1.2" '
        f'stroke-dasharray="5 3"/>',
        _label(326, 90, "pivot", A300, 8.5, "end"),
        f'<line x1="44" x2="330" y1="154" y2="154" stroke={UP!r} stroke-width="1.2" '
        f'stroke-dasharray="5 3"/>',
        _label(326, 150, "yesterday low", UP, 8.5, "end"),
    ]
    for x, o, c, h, l in [(60, 100, 92, 86, 106), (80, 92, 104, 86, 110),
                          (100, 104, 96, 90, 110), (120, 96, 60, 54, 100),
                          (140, 60, 40, 34, 66), (160, 40, 56, 36, 62),
                          (180, 56, 74, 50, 80), (200, 74, 92, 68, 98),
                          (220, 92, 78, 72, 98), (240, 78, 58, 50, 84),
                          (260, 58, 44, 38, 64), (280, 44, 60, 40, 66)]:
        inner.append(_candle(x, o, c, h, l, 10))
    inner.append(f'<circle cx="145" cy="36" r="10" fill="none" stroke="{DOWN}" '
                 f'stroke-width="1.3"/>')
    return _frame("".join(inner), 340, 176)


def zone_touches() -> str:
    """Why a level needs more than one touch."""
    inner = [
        _label(0, 13, "One touch is a coincidence. Three is a level.", MUTED, 9.5),
        _zone(96, 18, UP, "", 330),
        _label(6, 108, "SUPPORT", UP, 9, "start", "500"),
    ]
    pts = [(20, 60), (46, 104), (72, 64), (104, 40), (130, 106), (156, 56),
           (186, 30), (212, 104), (240, 62), (268, 34), (300, 100), (326, 52)]
    d = " ".join(f"{'M' if i == 0 else 'L'}{x} {y}" for i, (x, y) in enumerate(pts))
    inner.append(f'<path d="{d}" fill="none" stroke="{TEXT}" stroke-width="1.6" '
                 f'stroke-linejoin="round" opacity=".75"/>')
    for i, (x, y) in enumerate(pts):
        if y > 95:
            n = [46, 130, 212, 300].index(x) + 1 if x in (46, 130, 212, 300) else 0
            inner.append(f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{UP}" '
                         f'stroke-width="1.3"/>')
            if n:
                inner.append(_label(x, y + 3.5, str(n), UP, 8.5, "middle", "600"))
    inner.append(_label(166, 160, "Each bounce makes the next one more likely",
                        MUTED, 9.5, "middle"))
    return _frame("".join(inner), 340, 170)


def lot_size() -> str:
    """How position size follows from risk, not from a guess."""
    rows = [
        ("Account", "$1,000", TEXT),
        ("Risk per trade", "2%  =  $20", A300),
        ("Stop distance", "40 pips", DOWN),
        ("So each pip", "$0.50", MUTED),
        ("Lot size", "0.05", UP),
    ]
    inner = [_label(0, 13, "The size is calculated, never guessed", MUTED, 9.5)]
    y = 38
    for label, value, col in rows:
        last = label == "Lot size"
        inner += [
            f'<rect x="0" y="{y-14}" width="340" height="26" rx="5" '
            f'fill="{RAISED if last else "transparent"}"/>',
            _label(10, y + 3, label, MUTED if not last else TEXT, 10.5),
            f'<text x="330" y="{y+3}" fill="{col}" font-size="11.5" '
            f'font-family="{MONO}" font-weight="500" text-anchor="end">{value}</text>',
        ]
        if not last:
            inner.append(f'<line x1="0" x2="340" y1="{y+12}" y2="{y+12}" '
                         f'stroke="{GRID}" stroke-width="1"/>')
        y += 30
    inner.append(_label(170, y + 8, "Change the stop and the size changes with it",
                        FAINT, 9, "middle"))
    return _frame("".join(inner), 340, y + 20)


def session_clock() -> str:
    """When each market is liquid."""
    bars = [("Sydney", 21, 6, FAINT), ("Tokyo", 0, 9, A300),
            ("London", 7, 16, ACCENT), ("New York", 12, 21, UP)]
    inner = [_label(0, 13, "Each market has its own hours — and its own energy",
                    MUTED, 9.5)]
    y = 34
    for name, a, b, col in bars:
        segs = [(a, b)] if a < b else [(a, 24), (0, b)]
        inner.append(_label(0, y + 10, name, TEXT, 10))
        for s, e in segs:
            x = 66 + s / 24 * 262
            w = (e - s) / 24 * 262
            inner.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="13" '
                         f'rx="3" fill="{col}" opacity=".55"/>')
        y += 24
    inner.append(f'<line x1="66" x2="328" y1="{y+2}" y2="{y+2}" stroke="{GRID}" '
                 f'stroke-width="1"/>')
    for h in (0, 6, 12, 18, 24):
        x = 66 + h / 24 * 262
        inner.append(_label(x, y + 16, f"{h:02d}", FAINT, 8.5, "middle"))
    # the overlap that matters
    ox = 66 + 12 / 24 * 262
    ow = 4 / 24 * 262
    inner += [
        f'<rect x="{ox:.1f}" y="28" width="{ow:.1f}" height="{y-26}" fill="{WARN}" '
        f'opacity=".10" rx="3"/>',
        _label(ox + ow / 2, 24, "busiest", WARN, 8.5, "middle", "600"),
    ]
    inner.append(_label(170, y + 34, "London and New York overlap — the biggest moves",
                        MUTED, 9.5, "middle"))
    return _frame("".join(inner), 340, y + 44)


def confidence_bar(grade: str) -> str:
    """A / B / C as filled pips."""
    filled = {"A": 5, "B": 3, "C": 2}.get(grade, 0)
    col = {"A": UP, "B": A300, "C": WARN}.get(grade, FAINT)
    pips = "".join(
        f'<rect x="{i*13}" y="0" width="9" height="9" rx="2" '
        f'fill="{col if i < filled else RAISED}"/>' for i in range(5))
    return (f'<svg viewBox="0 0 65 9" width="65" height="9" '
            f'style="display:inline-block;vertical-align:middle">{pips}</svg>')


def strength_bar(value: int, color: str = ACCENT, width: int = 110) -> str:
    pct = max(0, min(100, value))
    return (f'<svg viewBox="0 0 {width} 6" width="{width}" height="6" '
            f'style="display:inline-block;vertical-align:middle">'
            f'<rect width="{width}" height="6" rx="3" fill="{RAISED}"/>'
            f'<rect width="{width*pct/100:.1f}" height="6" rx="3" fill="{color}"/></svg>')


def trade_lifecycle() -> str:
    """The five steps, as a flow."""
    steps = [("1", "Find the zone", "Support or resistance the price respects"),
             ("2", "Wait", "No reversal candle, no trade"),
             ("3", "Check the story", "Order block, gap, higher timeframes"),
             ("4", "Size it", "Stop distance decides the lots"),
             ("5", "Place and leave it", "Stop and target already set")]
    inner = []
    y = 16
    for n, title, desc in steps:
        inner += [
            f'<circle cx="13" cy="{y+6}" r="11" fill="{ACCENT}22" stroke="{ACCENT}" '
            f'stroke-width="1"/>',
            _label(13, y + 10, n, A300, 10.5, "middle", "600"),
            _label(34, y + 4, title, TEXT, 11.5, "start", "500"),
            _label(34, y + 18, desc, MUTED, 9.5),
        ]
        if n != "5":
            inner.append(f'<line x1="13" x2="13" y1="{y+19}" y2="{y+37}" '
                         f'stroke="{ACCENT}" stroke-width="1" opacity=".4"/>')
        y += 48
    return _frame("".join(inner), 340, y)
