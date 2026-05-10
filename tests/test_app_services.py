from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.app_services.error_presenter import build_controlled_error_payload
from src.app_services.execution_service import build_signal_from_analysis, build_trade_lifecycle_view_model
from src.trading.events import EventType, JournalEvent
from src.trading.models import PortfolioState


def test_execution_service_builds_signal_from_analysis() -> None:
    frame = pd.DataFrame(
        {"close": [100.0, 101.0], "signal": [0, 1]},
        index=pd.to_datetime(["2026-05-09", "2026-05-10"]),
    )
    result = {"df": frame}

    signal = build_signal_from_analysis(
        result,
        symbol="2330.TW",
        strategy_name="RSI_MACD",
        timeframe="1d",
        created_at=datetime(2026, 5, 10, 9, 0, 0),
    )

    assert signal is not None
    assert signal.symbol == "2330.TW"
    assert signal.side.value == "BUY"
    assert signal.metadata["reference_price"] == 101.0


def test_error_presenter_builds_controlled_error_payload() -> None:
    payload = build_controlled_error_payload(
        symbol="2330.TW",
        attempted_source="live_yfinance",
        fallback_attempted=True,
        diagnostics={"live_error": "unable to open database file"},
        message="Unable to load market data for 2330.TW",
    )

    assert payload["symbol"] == "2330.TW"
    assert payload["attempted_source"] == "live_yfinance"
    assert payload["fallback_attempted"] is True
    assert payload["diagnostics"]["live_error"] == "unable to open database file"


def test_execution_service_builds_trade_lifecycle_view_model() -> None:
    events = [
        JournalEvent(
            event_id="evt:signal",
            event_type=EventType.SIGNAL_EMITTED,
            aggregate_id="signal:1",
            payload={"symbol": "2330.TW"},
            created_at=datetime(2026, 5, 10, 9, 0, 0),
            market_time=datetime(2026, 5, 10, 9, 0, 0),
            processed_at=datetime(2026, 5, 10, 9, 0, 0),
        )
    ]

    view_model = build_trade_lifecycle_view_model(
        journal_events=events,
        portfolio_state=PortfolioState.initial(cash=1_000_000.0),
    )

    assert view_model.latest_signal["signal_id"] == "signal:1"
    assert view_model.latest_portfolio["cash"] == 1_000_000.0
