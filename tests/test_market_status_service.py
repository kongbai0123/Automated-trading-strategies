from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.app_services.market_status_service import build_market_status_items
from src.market_data import MarketDataResult


def _result(values: list[float]) -> MarketDataResult:
    return MarketDataResult(
        dataframe=pd.DataFrame(
            {
                "open": values,
                "high": values,
                "low": values,
                "close": values,
                "volume": [1000 for _ in values],
            },
            index=pd.date_range("2026-05-08", periods=len(values), freq="D"),
        ),
        source="live_yfinance",
        live_attempted=True,
        fallback_used=False,
        warnings=[],
        diagnostics={},
        data_freshness="live",
        last_bar_time=datetime(2026, 5, 9),
        is_stale=False,
    )


def test_market_status_items_use_market_data_service() -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_fetch(symbol: str, *, period: str, interval: str) -> MarketDataResult:
        calls.append((symbol, period, interval))
        return _result([100.0, 105.0])

    items = build_market_status_items(
        {"TAIEX": "^TWII", "BTC": "BTC-USD"},
        fetch_market_data=fake_fetch,
    )

    assert [(item.label, item.value, item.change_pct) for item in items] == [
        ("TAIEX", "105.00", 0.05),
        ("BTC", "105.00", 0.05),
    ]
    assert calls == [("^TWII", "5d", "1d"), ("BTC-USD", "5d", "1d")]


def test_market_status_items_degrade_when_source_fails() -> None:
    def failing_fetch(symbol: str, *, period: str, interval: str) -> MarketDataResult:
        raise RuntimeError("provider failed")

    items = build_market_status_items(
        {"TAIEX": "^TWII"}, fetch_market_data=failing_fetch
    )

    assert items[0].label == "TAIEX"
    assert items[0].value == "--"
    assert items[0].change_pct == 0.0
