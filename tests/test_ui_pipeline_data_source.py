from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from src.market_data import ControlledMarketDataError, MarketDataResult
from src.ui_pipeline import run_backtest_pipeline
from src.ui.components.data_status import build_data_status


def _market_result(source: str = "local_csv", fallback_used: bool = True) -> MarketDataResult:
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.0, 102.0, 101.0],
            "volume": [1000, 1100, 900],
        },
        index=pd.to_datetime(["2026-05-07", "2026-05-08", "2026-05-09"]),
    )
    return MarketDataResult(
        dataframe=frame,
        source=source,
        live_attempted=True,
        fallback_used=fallback_used,
        warnings=["Live data unavailable. Using local CSV fallback."] if fallback_used else [],
        diagnostics={"live_error": "unable to open database file"} if fallback_used else {},
        data_freshness="delayed",
        last_bar_time=datetime(2026, 5, 9),
        is_stale=fallback_used,
    )


def test_pipeline_metadata_contains_data_source_and_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.ui_pipeline.fetch_market_data", lambda *args, **kwargs: _market_result())

    result = run_backtest_pipeline(
        symbol="2330.TW",
        strategy_name="RSI_MACD",
        strategy_params={},
        transaction_cost=0.001,
        period="2y",
        interval="1d",
    )

    metadata = result["metadata"]
    assert metadata["data_source"] == "local_csv"
    assert metadata["fallback_used"] is True
    assert metadata["data_warnings"] == ["Live data unavailable. Using local CSV fallback."]
    assert metadata["data_diagnostics"]["live_error"] == "unable to open database file"
    assert metadata["data_freshness"] == "delayed"
    assert metadata["last_bar_time"] == datetime(2026, 5, 9)
    assert metadata["is_stale"] is True


def test_pipeline_raises_controlled_error_when_all_sources_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(*args, **kwargs):
        raise ControlledMarketDataError(
            symbol="2330.TW",
            attempted_source="live_yfinance",
            fallback_attempted=True,
            diagnostics={"live_error": "unable to open database file"},
        )

    monkeypatch.setattr("src.ui_pipeline.fetch_market_data", fake_fetch)

    with pytest.raises(ControlledMarketDataError, match="Unable to load market data for 2330.TW"):
        run_backtest_pipeline(
            symbol="2330.TW",
            strategy_name="RSI_MACD",
            strategy_params={},
            transaction_cost=0.001,
            period="2y",
            interval="1d",
        )


def test_ui_uses_warning_not_traceback_for_fallback_result() -> None:
    status = build_data_status(
        {
            "data_source": "local_csv",
            "fallback_used": True,
            "data_warnings": ["Live data unavailable. Using local CSV fallback."],
            "data_diagnostics": {"live_error": "unable to open database file"},
            "data_freshness": "delayed",
            "last_bar_time": datetime(2026, 5, 9),
            "is_stale": True,
        }
    )

    assert status.badge_label == "Local Cache"
    assert status.tone == "warning"
    assert "traceback" not in status.message.lower()
    assert "local csv fallback" in status.message.lower()
