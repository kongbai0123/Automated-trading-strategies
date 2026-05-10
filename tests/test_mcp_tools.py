from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.mcp_server.schemas import ensure_json_safe
from src.mcp_server.tools import MCPToolService


def _analysis_result() -> dict:
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    dataframe = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
            "volume": [1000, 1100, 1200],
            "signal": [0, 0, 1],
            "equity": [1_000_000.0, 1_001_000.0, 1_002_500.0],
        },
        index=index,
    )
    return {
        "df": dataframe,
        "kpi": {"return": 0.025, "win_rate": 0.5, "max_drawdown": -0.01},
        "metadata": {
            "symbol": "2330.TW",
            "strategy_name": "RSI_MACD",
            "data_source": "local_csv",
            "fallback_used": True,
            "data_warnings": ["fallback"],
            "last_bar_time": index[-1].to_pydatetime(),
            "is_stale": False,
        },
    }


def test_mcp_tools_are_listed_with_safe_execution_scope() -> None:
    service = MCPToolService(analysis_loader=lambda **_: _analysis_result())

    tools = service.list_tools()
    names = {tool["name"] for tool in tools}

    assert {
        "list_strategies",
        "run_strategy_analysis",
        "get_trade_lifecycle",
        "get_portfolio_snapshot",
        "get_journal_events",
        "simulate_order_intent",
    }.issubset(names)
    assert "submit_live_order" not in names


def test_run_strategy_analysis_returns_json_safe_summary() -> None:
    service = MCPToolService(analysis_loader=lambda **_: _analysis_result())

    result = service.call_tool(
        "run_strategy_analysis",
        {
            "symbol": "2330.TW",
            "strategy": "RSI_MACD",
            "timeframe": "1d",
            "period": "1mo",
        },
    )

    assert result["metadata"]["data_source"] == "local_csv"
    assert result["latest_bar"]["close"] == 12.5
    assert result["latest_signal"] == 1
    ensure_json_safe(result)


def test_simulate_order_intent_uses_paper_engine_and_journal() -> None:
    service = MCPToolService(analysis_loader=lambda **_: _analysis_result())
    service.call_tool(
        "run_strategy_analysis",
        {
            "symbol": "2330.TW",
            "strategy": "RSI_MACD",
            "timeframe": "1d",
            "period": "1mo",
        },
    )

    result = service.call_tool(
        "simulate_order_intent",
        {
            "symbol": "2330.TW",
            "strategy": "RSI_MACD",
            "timeframe": "1d",
            "requested_quantity": 10,
        },
    )

    assert result["mode"] == "paper"
    assert result["intent"]["symbol"] == "2330.TW"
    assert result["risk_decision"]["approved"] is True
    assert result["order"]["status"] == "FILLED"
    assert service.call_tool("get_journal_events", {"mode": "paper", "limit": 5})


def test_json_safe_serialization_handles_datetime_and_dataframe_values() -> None:
    payload = {
        "created_at": datetime(2026, 5, 10, 12, 0, 0),
        "series_value": pd.Timestamp("2026-05-10"),
    }

    assert ensure_json_safe(payload) == {
        "created_at": "2026-05-10T12:00:00",
        "series_value": "2026-05-10T00:00:00",
    }
