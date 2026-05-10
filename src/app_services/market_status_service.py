from __future__ import annotations

from collections.abc import Mapping

from src.market_data import (
    MarketDataResult,
    fetch_market_data as default_fetch_market_data,
)
from src.ui.components.market_bar import MarketStatusItem


def build_market_status_items(
    tickers: Mapping[str, str],
    *,
    fetch_market_data=default_fetch_market_data,
) -> list[MarketStatusItem]:
    items: list[MarketStatusItem] = []
    for label, symbol in tickers.items():
        try:
            result: MarketDataResult = fetch_market_data(
                symbol, period="5d", interval="1d"
            )
            close = result.dataframe["close"].dropna()
            if len(close) >= 2:
                current = float(close.iloc[-1])
                previous = float(close.iloc[-2])
                change_pct = 0.0 if previous == 0 else (current - previous) / previous
            elif len(close) == 1:
                current = float(close.iloc[-1])
                change_pct = 0.0
            else:
                current = 0.0
                change_pct = 0.0

            items.append(
                MarketStatusItem(
                    label=label,
                    value=f"{current:,.2f}",
                    change_pct=change_pct,
                )
            )
        except Exception:
            items.append(MarketStatusItem(label=label, value="--", change_pct=0.0))
    return items
