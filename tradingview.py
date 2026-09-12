"""
tradingview.py — TradingView chart widgets, embedded.

TradingView has no public data API, but their widgets are free to embed and
render real live charts with no key and no rate limit — which sidesteps every
data problem a cloud host has. Zonelock draws its own levels on its own chart;
this gives you TradingView's chart beside it, on the same symbol.

    from tradingview import advanced_chart, TV_SYMBOLS
    st.components.v1.html(advanced_chart("XAUUSD"), height=520)
"""

from __future__ import annotations

import json
import uuid

# Zonelock symbol → TradingView ticker. OANDA and FX_IDC are free, no login.
TV_SYMBOLS = {
    "XAUUSD": "OANDA:XAUUSD",
    "EURUSD": "FX:EURUSD",
    "GBPUSD": "FX:GBPUSD",
    "USDJPY": "FX:USDJPY",
    "AUDUSD": "FX:AUDUSD",
    "USDCAD": "FX:USDCAD",
    "US30":   "OANDA:US30USD",
    "NAS100": "OANDA:NAS100USD",
    "SPX500": "OANDA:SPX500USD",
    "BTCUSD": "BINANCE:BTCUSDT",
    "ETHUSD": "BINANCE:ETHUSDT",
    "USOIL":  "TVC:USOIL",
}

TV_INTERVAL = {"M5": "5", "M15": "15", "M30": "30", "H1": "60",
               "H4": "240", "D1": "D", "W1": "W"}

THEME = {
    "bg": "#161826", "grid": "rgba(233,233,237,0.07)", "up": "#5fbf8f",
    "down": "#e07b87", "text": "#9397ab", "accent": "#9184d9",
}


def advanced_chart(symbol: str, timeframe: str = "M15", height: int = 520,
                   studies: list | None = None, levels: list | None = None) -> str:
    """
    Full TradingView chart, themed to match Zonelock.
    `levels` is a list of (price, label, colour) drawn as horizontal lines.
    """
    tv = TV_SYMBOLS.get(symbol, "OANDA:XAUUSD")
    interval = TV_INTERVAL.get(timeframe, "15")
    cid = "tv_" + uuid.uuid4().hex[:8]

    config = {
        "autosize": True,
        "symbol": tv,
        "interval": interval,
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "backgroundColor": THEME["bg"],
        "gridColor": THEME["grid"],
        "hide_top_toolbar": False,
        "hide_legend": False,
        "allow_symbol_change": True,
        "save_image": False,
        "calendar": False,
        "withdateranges": True,
        "hide_volume": True,
        "support_host": "https://www.tradingview.com",
        "container_id": cid,
        "studies": studies or [],
        "overrides": {
            "paneProperties.background": THEME["bg"],
            "paneProperties.backgroundType": "solid",
            "paneProperties.vertGridProperties.color": THEME["grid"],
            "paneProperties.horzGridProperties.color": THEME["grid"],
            "scalesProperties.textColor": THEME["text"],
            "scalesProperties.lineColor": THEME["grid"],
            "mainSeriesProperties.candleStyle.upColor": THEME["up"],
            "mainSeriesProperties.candleStyle.downColor": THEME["down"],
            "mainSeriesProperties.candleStyle.borderUpColor": THEME["up"],
            "mainSeriesProperties.candleStyle.borderDownColor": THEME["down"],
            "mainSeriesProperties.candleStyle.wickUpColor": THEME["up"],
            "mainSeriesProperties.candleStyle.wickDownColor": THEME["down"],
        },
    }

    level_html = ""
    if levels:
        rows = "".join(
            f"<div style='display:flex;align-items:center;gap:8px;padding:5px 0;"
            f"border-bottom:1px solid rgba(233,233,237,.08)'>"
            f"<span style='width:22px;height:2px;background:{c};flex:none'></span>"
            f"<span style='flex:1;font-size:11.5px;color:#e9e9ed'>{label}</span>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;"
            f"color:{c}'>{price}</span></div>"
            for price, label, c in levels)
        level_html = (
            f"<div style='background:#1e2030;border:1px solid rgba(233,233,237,.10);"
            f"border-radius:9px;padding:10px 13px;margin-top:9px'>"
            f"<div style='font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;"
            f"color:{THEME['accent']};margin-bottom:4px'>Draw these on the chart</div>"
            f"{rows}</div>")

    return f"""
<div style="background:{THEME['bg']};font-family:Inter,system-ui,sans-serif">
  <div id="{cid}" style="height:{height - (150 if levels else 0)}px;width:100%"></div>
  {level_html}
</div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
  (function () {{
    function boot() {{
      if (!window.TradingView) {{ setTimeout(boot, 220); return; }}
      new TradingView.widget({json.dumps(config)});
    }}
    boot();
  }})();
</script>
"""


def mini_chart(symbol: str, height: int = 180) -> str:
    """A compact sparkline for the market grid."""
    tv = TV_SYMBOLS.get(symbol, "OANDA:XAUUSD")
    cid = "tvm_" + uuid.uuid4().hex[:8]
    config = {
        "symbol": tv, "width": "100%", "height": height, "locale": "en",
        "dateRange": "1D", "colorTheme": "dark", "isTransparent": True,
        "autosize": False, "largeChartUrl": "",
        "chartOnly": False, "noTimeScale": True,
    }
    return f"""
<div class="tradingview-widget-container" id="{cid}"
     style="background:transparent">
  <div class="tradingview-widget-container__widget"></div>
</div>
<script type="text/javascript"
  src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js"
  async>{json.dumps(config)}</script>
"""


def ticker_tape(symbols: list[str], height: int = 46) -> str:
    """The scrolling price strip along the top."""
    items = [{"proName": TV_SYMBOLS.get(s, s), "title": s} for s in symbols]
    config = {"symbols": items, "showSymbolLogo": False, "isTransparent": True,
              "displayMode": "adaptive", "colorTheme": "dark", "locale": "en"}
    return f"""
<div class="tradingview-widget-container" style="background:transparent;height:{height}px">
  <div class="tradingview-widget-container__widget"></div>
</div>
<script type="text/javascript"
  src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js"
  async>{json.dumps(config)}</script>
"""
