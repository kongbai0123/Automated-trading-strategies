from __future__ import annotations

from src.app_services.timeframe_options import (
    normalize_period_for_timeframe,
    period_options_for_timeframe,
)


def test_intraday_timeframes_offer_short_periods_only() -> None:
    options = period_options_for_timeframe("1m")

    assert options == ["1d", "5d", "7d"]
    assert "2y" not in options


def test_daily_timeframe_keeps_longer_research_periods() -> None:
    options = period_options_for_timeframe("1d")

    assert "1mo" in options
    assert "5y" in options


def test_invalid_period_is_normalized_for_selected_timeframe() -> None:
    assert normalize_period_for_timeframe("2y", "1m") == "1d"
    assert normalize_period_for_timeframe("3mo", "1d") == "3mo"
