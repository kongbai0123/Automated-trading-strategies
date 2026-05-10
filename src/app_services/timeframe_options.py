from __future__ import annotations

TIMEFRAME_PERIOD_OPTIONS = {
    "1m": ["1d", "5d", "7d"],
    "5m": ["1d", "5d", "7d", "1mo"],
    "15m": ["1d", "5d", "1mo", "3mo"],
    "30m": ["5d", "1mo", "3mo"],
    "60m": ["5d", "1mo", "3mo", "6mo"],
    "1d": ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    "1wk": ["6mo", "1y", "2y", "5y", "10y"],
    "1mo": ["1y", "2y", "5y", "10y"],
}


def period_options_for_timeframe(timeframe: str) -> list[str]:
    return list(TIMEFRAME_PERIOD_OPTIONS.get(timeframe, TIMEFRAME_PERIOD_OPTIONS["1d"]))


def normalize_period_for_timeframe(period: str, timeframe: str) -> str:
    options = period_options_for_timeframe(timeframe)
    if period in options:
        return period
    return options[0]
