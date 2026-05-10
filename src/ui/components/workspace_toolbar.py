from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import streamlit as st


@dataclass(frozen=True)
class ToolbarState:
    symbol: str
    timeframe: str
    period: str
    strategy_name: str
    execution_mode: str


def render_workspace_toolbar(
    *,
    symbols: Iterable[str],
    selected_symbol: str,
    timeframes: Iterable[str],
    selected_timeframe: str,
    periods: Iterable[str],
    selected_period: str,
    strategies: Iterable[str],
    selected_strategy: str,
    execution_modes: Iterable[str],
    selected_execution_mode: str,
) -> ToolbarState:
    col_symbol, col_timeframe, col_period, col_strategy, col_mode = st.columns(
        [1.5, 1, 1, 1.4, 1.1]
    )
    with col_symbol:
        symbol = st.selectbox(
            "Symbol", list(symbols), index=list(symbols).index(selected_symbol)
        )
    with col_timeframe:
        timeframe = st.selectbox(
            "Timeframe",
            list(timeframes),
            index=list(timeframes).index(selected_timeframe),
        )
    with col_period:
        period = st.selectbox(
            "Period", list(periods), index=list(periods).index(selected_period)
        )
    with col_strategy:
        strategy_name = st.selectbox(
            "Strategy",
            list(strategies),
            index=list(strategies).index(selected_strategy),
        )
    with col_mode:
        execution_mode = st.selectbox(
            "Execution",
            list(execution_modes),
            index=list(execution_modes).index(selected_execution_mode),
        )
    return ToolbarState(
        symbol=symbol,
        timeframe=timeframe,
        period=period,
        strategy_name=strategy_name,
        execution_mode=execution_mode,
    )
